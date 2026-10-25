import asyncio
import base64
import contextlib
import io
import logging
import re
from collections.abc import AsyncIterator
from contextvars import ContextVar

import httpx
from openai import AsyncOpenAI
from PIL import Image, ImageOps

from app.core.config import get_settings
from app.features.documents.ingestion import image_preprocess as pp
from app.features.documents.ingestion.image_orientation import (
    PROBE_PROMPT,
    choose_rotation,
    detect_rotation_osd,
    parse_probe_answer,
    rotate_clockwise,
)
from app.features.documents.ingestion.layout_helper import crop_image_box, detect_tables_with_mistral

logger = logging.getLogger(__name__)

_OCR_ATTEMPTS = 3


class _ContentFiltered(Exception):
    """The gateway answered `finish_reason=content_filter` with no text. Seen with Gemini on some government letters
    (stamps/signatures): about half of the identical requests came back empty, the rest were fine - so it is retried."""

# The SDK default connect timeout is 5s: with dozens of pages in flight, each opening its own TLS connection to the gateway,
# connects time out (seen as "Request timed out" + retries, tripling the load). A generous connect timeout, plus one
# shared client per document (see `ocr_client_session`), avoids that storm.
_OCR_TIMEOUT = httpx.Timeout(180.0, connect=30.0)
_session_client: ContextVar[AsyncOpenAI | None] = ContextVar("ocr_session_client", default=None)


@contextlib.asynccontextmanager
async def ocr_client_session() -> AsyncIterator[None]:
    """Share one client (connection pool, keep-alive) between all `extract_text_from_image` calls made inside this block.
    A ContextVar, not a global: every ingestion job runs on its own event loop, and tasks created inside inherit it."""
    settings = get_settings()
    client = AsyncOpenAI(base_url=settings.llm_api_base_url, api_key=settings.llm_api_key, timeout=_OCR_TIMEOUT)
    token = _session_client.set(client)
    try:
        yield
    finally:
        _session_client.reset(token)
        await client.close()

SYSTEM_OCR_PROMPT = (
    "شما یک موتور فوق‌دقیق OCR برای اسناد فنی، عمرانی و مهندسی هستید.\n\n"
    "قوانین استخراج:\n"
    "۱. در صورت وجود جدول، خروجی فقط و فقط ساختار جدول استاندارد Markdown باشد (بدون تگ کد، بدون مقدمه و بدون متن اضافی).\n"
    "۲. در خواندن ارقام فارسی (به‌ویژه دندانه‌های ۲، ۳، ۴ و تفاوت ۶ با ۴) نهایت دقت را داشته باشید و هرگز دندانه‌ها را حدس نزنید.\n"
    "۳. ستون‌های مختصات (Easting و Northing)، ارتفاع (Height) و ضریب مقیاس (Scale Factor) باید رقم‌به‌رقم و با حفظ تمام صفرهای اعشار استخراج شوند.\n"
    "۴. تمامی ردیف‌ها را از ابتدا تا انتها بدون خلاصه کردن (...) استخراج کنید.\n"
    "۵. تمام متون سربرگ، مهر، امضا یا توضیحات خارج از جدول را نیز با دقت کامل و بدون دخل و تصرف رونویسی کنید.\n"
    "۶. اگر تصویر هیچ متن یا اطلاعات معناداری ندارد، یک رشته خالی برگردانید."
)

SYSTEM_TABLE_OCR_PROMPT = (
    "شما یک موتور فوق‌دقیق OCR برای اسناد فنی، عمرانی و مهندسی هستید.\n\n"
    "دستورالعمل‌های حیاتی استخراج:\n"
    "۱. سربرگ و اطلاعات اولیه: اگر در بالای تصویر متونی مانند عنوان طرح، عنوان پروژه، نام شرکت، کارفرما، پیمانکار، شماره قرارداد، تاریخ صورتجلسه، کیلومتراژ یا شماره زون وجود دارد، آن‌ها را به طور کامل در ابتدای خروجی استخراج کنید.\n"
    "۲. جدول داده‌ها: ساختار جدول را به صورت جدول استاندارد Markdown استخراج کنید. در خواندن ارقام فارسی (به‌ویژه دندانه‌های ۲، ۳، ۴ و تفاوت ۶ با ۴) نهایت دقت را داشته باشید و هرگز دندانه‌ها را حدس نزنید.\n"
    "۳. ستون‌های مختصات (Easting و Northing)، ارتفاع (Height) و ضریب مقیاس (Scale Factor) باید رقم‌به‌رقم و با حفظ تمام صفرهای اعشار استخراج شوند.\n"
    "۴. تمامی ردیف‌ها را از ابتدا تا انتها بدون خلاصه کردن (...) استخراج کنید.\n"
    "۵. پاورقی و امضاها: اگر در زیر جدول اطلاعاتی مانند مشخصات کارفرما، مشاور، پیمانکار، نام افراد و امضاها وجود دارد، آن‌ها را در انتهای خروجی بیاورید."
)


def _to_rgb(pil_img: Image.Image) -> Image.Image:
    """EXIF orientation applied; alpha/palette flattened on white; always RGB."""
    pil_img = ImageOps.exif_transpose(pil_img)
    if pil_img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", pil_img.size, (255, 255, 255))
        if pil_img.mode == "P":
            pil_img = pil_img.convert("RGBA")
        mask = pil_img.split()[-1] if pil_img.mode in ("RGBA", "LA") else None
        background.paste(pil_img, mask=mask)
        return background
    return pil_img if pil_img.mode == "RGB" else pil_img.convert("RGB")


def _encode_for_ocr(pil_img: Image.Image, max_dimension: int | None = None, quality: int | None = None) -> tuple[bytes, str]:
    """Downscales an oversized image and encodes it as high-quality JPEG (95 keeps decimal dots and small digits clean)."""
    settings = get_settings()
    target_max_dim = max_dimension if max_dimension is not None else getattr(settings, "ocr_max_image_dimension", 2560)
    target_quality = quality if quality is not None else getattr(settings, "ocr_jpeg_quality", 95)
    w, h = pil_img.size
    if max(w, h) > target_max_dim:
        scale = target_max_dim / max(w, h)
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    out_buf = io.BytesIO()
    pil_img.save(out_buf, format="JPEG", quality=target_quality)
    return out_buf.getvalue(), "jpeg"


def optimize_image_for_ocr(
    image_bytes: bytes,
    max_dimension: int | None = None,
    quality: int | None = None,
) -> tuple[bytes, str]:
    """Resizes excessively large images and converts to high-quality JPEG to balance latency and OCR precision.
    Applies EXIF orientation and preserves fine decimal and tabular details."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            return _encode_for_ocr(_to_rgb(pil_img), max_dimension, quality)
    except Exception as exc:
        logger.debug("Image optimization skipped (%s); using original bytes.", exc)
        return image_bytes, "png"


PREPROCESS_VERSION = 2  # bump when the pre-processing code changes in a way that can change the OCR text


def preprocess_signature() -> str:
    """Part of the OCR cache key: the same bytes read with different pre-processing may give different text."""
    settings = get_settings()
    flags = "".join(
        str(int(bool(getattr(settings, name, False)))) for name in ("ocr_auto_orient", "ocr_deskew", "ocr_crop_margins")
    )
    method = getattr(settings, "ocr_orient_method", "hybrid") if getattr(settings, "ocr_auto_orient", False) else "-"
    return f"pp{PREPROCESS_VERSION}.{flags}.{method}"


def _clean_image(pil_img: Image.Image, deskew: bool, crop: bool) -> Image.Image:
    if deskew:
        pil_img = pp.deskew(pil_img)
    if crop:
        pil_img = pp.crop_margins(pil_img)
    return pil_img


def _vision_client() -> AsyncOpenAI:
    settings = get_settings()
    return _session_client.get() or AsyncOpenAI(
        base_url=settings.llm_api_base_url, api_key=settings.llm_api_key, timeout=_OCR_TIMEOUT
    )


async def _probe_rotation(thumb: Image.Image) -> int | None:
    """One cheap question to the vision model: does this (low-resolution) page need rotating? None = no usable answer."""
    settings = get_settings()
    buf = io.BytesIO()
    thumb.convert("RGB").save(buf, format="JPEG", quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    response = await _vision_client().chat.completions.create(
        model=getattr(settings, "llm_vision_model", None) or getattr(settings, "llm_model", "gpt-4o"),
        messages=[{"role": "user", "content": [
            {"type": "text", "text": PROBE_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]}],
        max_tokens=60,
    )
    return parse_probe_answer(response.choices[0].message.content or "")


async def prepare_pil_image_for_ocr(
    image_bytes: bytes, rotation: int | None = None, report: dict | None = None
) -> Image.Image | None:
    """Decodes, filters blank images, rotates upright, and cleans an image for OCR.
    Returns the upright PIL Image or None for blank images."""
    settings = get_settings()
    # Pillow/numpy work is CPU-bound: off the event loop so other pages' requests aren't delayed behind it.
    pil_img = await asyncio.to_thread(lambda: _to_rgb(Image.open(io.BytesIO(image_bytes))))
    if getattr(settings, "ocr_skip_blank_images", True) and await asyncio.to_thread(pp.is_blank, pil_img):
        return None
    if rotation in (0, 90, 180, 270):
        degrees = rotation
        if degrees:
            pil_img = await asyncio.to_thread(rotate_clockwise, pil_img, degrees)
        if report is not None:
            report["rotation"] = degrees
    elif getattr(settings, "ocr_auto_orient", True) and min(pil_img.size) >= settings.ocr_orient_min_dimension:
        method = getattr(settings, "ocr_orient_method", "hybrid")
        degrees = await choose_rotation(
            pil_img,
            method=method,
            probe=_probe_rotation,
            osd=lambda image: detect_rotation_osd(image, settings.ocr_osd_concurrency),
            min_confidence=settings.ocr_orient_osd_min_confidence,
            upright_confidence=settings.ocr_orient_osd_upright_confidence,
        )
        if degrees:
            logger.debug("OCR: page rotated %d degrees clockwise to be upright (%s)", degrees, method)
            pil_img = await asyncio.to_thread(rotate_clockwise, pil_img, degrees)
        if report is not None:
            report["rotation"] = degrees
    deskew = getattr(settings, "ocr_deskew", False)
    crop = getattr(settings, "ocr_crop_margins", False)
    if deskew or crop:
        pil_img = await asyncio.to_thread(_clean_image, pil_img, deskew, crop)
    return pil_img


async def prepare_image_for_ocr(
    image_bytes: bytes, rotation: int | None = None, report: dict | None = None
) -> tuple[bytes, str] | None:
    """Decode -> (skip blank) -> (rotate upright) -> (deskew, crop empty borders) -> downscale + JPEG.
    Returns None for a blank image (nothing to read, no API call). Anything unexpected falls back to the plain
    `optimize_image_for_ocr`, so pre-processing can only ever be skipped, never fail an ingestion."""
    try:
        pil_img = await prepare_pil_image_for_ocr(image_bytes, rotation=rotation, report=report)
        if pil_img is None:
            return None
        return await asyncio.to_thread(_encode_for_ocr, pil_img)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Image pre-processing failed (%s); sending the plain optimized image.", exc)
        return await asyncio.to_thread(optimize_image_for_ocr, image_bytes)


# Appended to the prompt on the n-th content-filter retry (n = 1, 2, ...): a slightly different request, same instructions.
_RETRY_PROMPT_SUFFIXES = (
    "\n\nنکته: خروجی را دقیقاً طبق دستورالعمل‌های بالا بنویس.",
    "\n\nیادآوری: فقط متن و داده‌های موجود در تصویر را استخراج کن.",
)


def _vary_image_for_retry(jpeg_b64: str, retry: int) -> str:
    """A barely different JPEG of the same page for a retry after a content-filter refusal: a 10 px white border (+2% scale
    from the second retry on). Never sends the exact same bytes twice, in case the refusal depends on the input."""
    with Image.open(io.BytesIO(base64.b64decode(jpeg_b64))) as img:
        img = img.convert("RGB")
        if retry >= 2:
            img = img.resize((int(img.width * 0.98), int(img.height * 0.98)), Image.Resampling.LANCZOS)
        img = ImageOps.expand(img, border=10 * min(retry, 2), fill="white")
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=95)
    return base64.b64encode(out.getvalue()).decode("utf-8")


async def _vision_chat(client: AsyncOpenAI, model: str, prompt: str, mime_type: str, b64_img: str, max_tokens: int):
    """One vision request with the shared retry policy: transient errors (`_OCR_ATTEMPTS`) and random content-filter
    refusals (`OCR_CONTENT_FILTER_RETRIES`, own budget; each retry sends a slightly different image and prompt, see
    `_vary_image_for_retry`). Raises when the budget is spent."""
    retries = getattr(get_settings(), "ocr_content_filter_retries", 2)
    base_b64, base_prompt, mime = b64_img, prompt, mime_type
    attempt = filtered = 0
    while True:
        attempt += 1
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/{mime_type};base64,{b64_img}", "detail": "high"},
                            },
                        ],
                    }
                ],
                max_tokens=max_tokens,
            )
            choice = response.choices[0]
            if getattr(choice, "finish_reason", None) == "content_filter" and not (choice.message.content or "").strip():
                raise _ContentFiltered("finish_reason=content_filter with empty content")
            return response
        except _ContentFiltered as exc:
            attempt -= 1  # not counted against the error budget below
            filtered += 1
            if filtered > retries:
                raise
            logger.warning("Vision request refused (%s); retry %d/%d with a slightly different image and prompt", exc, filtered, retries)
            try:
                b64_img = await asyncio.to_thread(_vary_image_for_retry, base_b64, filtered)
                mime_type = "jpeg"
            except Exception as vary_exc:  # noqa: BLE001 - not an image we can re-encode: retry as it is
                logger.debug("could not vary the image for the retry (%s)", vary_exc)
                b64_img, mime_type = base_b64, mime
            prompt = base_prompt + _RETRY_PROMPT_SUFFIXES[min(filtered, len(_RETRY_PROMPT_SUFFIXES)) - 1]
            await asyncio.sleep(1.0)
        except Exception as exc:  # transient gateway/rate-limit errors are common during bulk ingestion
            if attempt == _OCR_ATTEMPTS:
                raise
            logger.warning("Vision request attempt %d/%d failed (%s); retrying", attempt, _OCR_ATTEMPTS, exc)
            await asyncio.sleep(2.0 * attempt)


def _vision_model() -> str:
    settings = get_settings()
    return getattr(settings, "llm_vision_model", None) or getattr(settings, "llm_model", "gpt-4o")


def _is_redundant_text(snippet: str, full_text: str) -> bool:
    """Returns True if most significant words of snippet already appear in full_text."""
    if not snippet or not snippet.strip():
        return True
    words = [w for w in re.findall(r"[\w\d\-]{3,}", snippet.lower()) if len(w) >= 3]
    if not words:
        return False
    full_lower = full_text.lower()
    matches = sum(1 for w in words if w in full_lower)
    return (matches / len(words)) >= 0.5


async def extract_text_from_image(image_bytes: bytes, image_format: str = "png", report: dict | None = None) -> str:
    """Uses a vision-capable LLM to perform OCR and structured data extraction from an image.
    When tables are detected via Mistral layout analysis, crops each table for high-resolution
    vision extraction, preserving surrounding header and footer metadata.
    Automatically falls back to full-page vision OCR if table detection fails or no tables are found.
    `report` (optional) receives `rotation` - the clockwise degrees the image was turned to be upright - when it is known."""
    settings = get_settings()
    if not getattr(settings, "ocr_enabled", True):
        return ""

    if not image_bytes or len(image_bytes) < 100:
        return ""

    if not settings.llm_api_key:
        logger.debug("LLM API key is empty, skipping Vision OCR.")
        return ""

    try:
        pil_img = None
        try:
            pil_img = await prepare_pil_image_for_ocr(image_bytes, report=report)
        except Exception:
            pil_img = None

        if pil_img is None:
            prepared = await prepare_image_for_ocr(image_bytes, report=report)
            if prepared is None:
                logger.debug("Blank image, skipping Vision OCR.")
                return ""
            optimized_bytes, mime_type = prepared
        else:
            # Two-stage table layout detection (Mistral OCR -> Gemini Crop)
            mistral_key = getattr(settings, "effective_mistral_api_key", "") or getattr(settings, "mistral_api_key", "") or getattr(settings, "mistral_key", "")
            if getattr(settings, "ocr_two_stage_enabled", True) and mistral_key:
                try:
                    layout_res = await detect_tables_with_mistral(pil_img, padding=30)
                    boxes = getattr(layout_res, "table_boxes", layout_res) if layout_res else []
                    if boxes:
                        logger.info("Two-stage OCR: extracting %d table crop(s) with vision model.", len(boxes))
                        extracted_tables: list[str] = []
                        for box in boxes:
                            cropped = crop_image_box(pil_img, box)
                            crop_bytes, crop_mime = await asyncio.to_thread(_encode_for_ocr, cropped)
                            b64_crop = base64.b64encode(crop_bytes).decode("utf-8")
                            resp = await _vision_chat(
                                _vision_client(),
                                _vision_model(),
                                SYSTEM_TABLE_OCR_PROMPT,
                                crop_mime,
                                b64_crop,
                                settings.ocr_max_tokens,
                            )
                            content = (resp.choices[0].message.content or "").strip()
                            if content and content not in ("---", "N/A", "none", "خالی", "None"):
                                extracted_tables.append(content)

                        if extracted_tables:
                            combined_tables = "\n\n".join(extracted_tables)

                            # Stitch header & footer metadata if not already present in table output
                            header_parts: list[str] = []
                            if getattr(layout_res, "header_text", "") and not _is_redundant_text(layout_res.header_text, combined_tables):
                                header_parts.append(layout_res.header_text)
                            if getattr(layout_res, "pre_table_text", "") and not _is_redundant_text(layout_res.pre_table_text, combined_tables):
                                header_parts.append(layout_res.pre_table_text)

                            footer_parts: list[str] = []
                            if getattr(layout_res, "post_table_text", "") and not _is_redundant_text(layout_res.post_table_text, combined_tables):
                                footer_parts.append(layout_res.post_table_text)
                            if getattr(layout_res, "footer_text", "") and not _is_redundant_text(layout_res.footer_text, combined_tables):
                                footer_parts.append(layout_res.footer_text)

                            final_sections: list[str] = []
                            if header_parts:
                                final_sections.append("### [سربرگ و مشخصات سند]\n" + "\n\n".join(header_parts))
                            final_sections.append(combined_tables)
                            if footer_parts:
                                final_sections.append("### [پاورقی و اطلاعات تکمیلی / امضاها]\n" + "\n\n".join(footer_parts))

                            return "\n\n".join(final_sections)
                except Exception as layout_exc:  # noqa: BLE001
                    logger.warning("Two-stage table extraction error (%s); falling back to full-page OCR.", layout_exc)

            optimized_bytes, mime_type = await asyncio.to_thread(_encode_for_ocr, pil_img)

        # Fallback / Default: full-page Vision OCR
        b64_img = base64.b64encode(optimized_bytes).decode("utf-8")
        response = await _vision_chat(
            _vision_client(), _vision_model(), SYSTEM_OCR_PROMPT, mime_type, b64_img, settings.ocr_max_tokens
        )
        cleaned = (response.choices[0].message.content or "").strip()
        if cleaned in ("---", "N/A", "none", "خالی", "None", ""):
            return ""
        return cleaned
    except Exception as exc:
        logger.warning("Vision OCR request failed for image (%s): %s", image_format, exc)
        return ""
