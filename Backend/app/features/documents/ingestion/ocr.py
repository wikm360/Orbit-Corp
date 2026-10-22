import asyncio
import base64
import contextlib
import io
import logging
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

logger = logging.getLogger(__name__)

_OCR_ATTEMPTS = 3
_FILTER_ATTEMPTS = 8  # content-filter answers are random per request and cheap (no output), so they get their own budget


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
    "شما یک موتور فوق‌العاده دقیق OCR و تحلیل تصویر اسناد، نقشه‌ها و صورتجلسات مهندسی و مالی هستید.\n"
    "وظیفه شما رونویسی و استخراج دقیق، کلمه به کلمه و رقم به رقم تمام متون، ارقام، ممیزها، جداول، مهرها و دست‌نوشته‌های موجود در این تصویر است.\n\n"
    "دستورالعمل‌های حیاتی:\n"
    "۱. جهت تصویر (Orientation): اگر تصویر به صورت چرخیده (۹۰، ۱۸۰ یا ۲۷۰ درجه) است، ابتدا جهت منطقی خواندن را تراز کنید و متون را بر اساس چینش طبیعی سطرها و ستون‌ها بخوانید.\n"
    "۲. دقت ارقام و اعداد (بسیار مهم): تمام اعداد، ارقام اعشاری (با ممیز یا نقطه اعشار)، صفرهای بعد از اعشار، واحدها، علامت‌های ریاضی و کیلومتراژها (مانند 2+100) را با دقت ۱۰۰٪ و بدون رند کردن یا تغییر رونویسی کنید. هرگز رقمی را حدس نزنید یا کوتاه نکنید.\n"
    "۳. جدول‌ها و صورت‌جلسات فنی/مالی: ساختار جداول را دقیقاً به جدول Markdown تبدیل کنید. ستون‌ها را به درستی تفکیک کنید. در سطرهای «مجموع»، «جمع کل» یا خلاصه کارکرد، ارقام واقعی سطر مجموع را بنویسید و اکیداً از کپی کردن ارقام سطرهای قبلی در سطر مجموع خودداری کنید.\n"
    "۴. مهرها، امضاها و سربرگ‌ها: تمام متون داخل مهرها (مانند نام شرکت، شماره ثبت، شماره کارگاه یا قطعه)، شماره و تاریخ قراردادها و شماره صورت‌جلسات را به طور کامل و جداگانه در متن بیاورید. از تولید اطلاعات فرضی و ساختگی (مانند شماره تلفن یا جملات تکراری ناموجود) اکیداً خودداری کنید.\n"
    "۵. اگر تصویر نمودار، فلوچارت یا دیاگرام است، علاوه بر متون آن، ساختار، ارقام و روابط آن را به دقت تشریح کنید.\n"
    "۶. اگر تصویر هیچ متن یا اطلاعات معناداری ندارد (فقط حاشیه، نویز یا خط ساده)، یک رشته خالی برگردانید.\n"
    "۷. خروجی باید فقط و فقط محتوای استخراج‌شده باشد، بدون هرگونه پیش‌گفتار، سلام، توضیح اضافی یا نتیجه‌گیری."
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


async def prepare_image_for_ocr(image_bytes: bytes) -> tuple[bytes, str] | None:
    """Decode -> (skip blank) -> (rotate upright) -> (deskew, crop empty borders) -> downscale + JPEG.
    Returns None for a blank image (nothing to read, no API call). Anything unexpected falls back to the plain
    `optimize_image_for_ocr`, so pre-processing can only ever be skipped, never fail an ingestion."""
    settings = get_settings()
    try:
        # Pillow/numpy work is CPU-bound: off the event loop so other pages' requests aren't delayed behind it.
        pil_img = await asyncio.to_thread(lambda: _to_rgb(Image.open(io.BytesIO(image_bytes))))
        if getattr(settings, "ocr_skip_blank_images", True) and await asyncio.to_thread(pp.is_blank, pil_img):
            return None
        if getattr(settings, "ocr_auto_orient", True) and min(pil_img.size) >= settings.ocr_orient_min_dimension:
            method = getattr(settings, "ocr_orient_method", "hybrid")
            degrees = await choose_rotation(
                pil_img,
                method=method,
                probe=_probe_rotation,
                osd=lambda image: detect_rotation_osd(image, settings.ocr_osd_concurrency),
                min_confidence=settings.ocr_orient_osd_min_confidence,
            )
            if degrees:
                logger.info("OCR: page rotated %d degrees clockwise to be upright (%s)", degrees, method)
                pil_img = await asyncio.to_thread(rotate_clockwise, pil_img, degrees)
        deskew = getattr(settings, "ocr_deskew", False)
        crop = getattr(settings, "ocr_crop_margins", False)
        if deskew or crop:
            pil_img = await asyncio.to_thread(_clean_image, pil_img, deskew, crop)
        return await asyncio.to_thread(_encode_for_ocr, pil_img)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Image pre-processing failed (%s); sending the plain optimized image.", exc)
        return await asyncio.to_thread(optimize_image_for_ocr, image_bytes)


async def extract_text_from_image(image_bytes: bytes, image_format: str = "png") -> str:
    """Uses a vision-capable LLM to perform OCR and structured data extraction from an image."""
    settings = get_settings()
    if not getattr(settings, "ocr_enabled", True):
        return ""

    if not image_bytes or len(image_bytes) < 100:
        return ""

    if not settings.llm_api_key:
        logger.debug("LLM API key is empty, skipping Vision OCR.")
        return ""

    try:
        prepared = await prepare_image_for_ocr(image_bytes)
        if prepared is None:
            logger.debug("Blank image, skipping Vision OCR.")
            return ""
        optimized_bytes, mime_type = prepared
        b64_img = base64.b64encode(optimized_bytes).decode("utf-8")

        vision_model = getattr(settings, "llm_vision_model", None) or getattr(settings, "llm_model", "gpt-4o")
        client = _vision_client()

        response = None
        attempt = filtered = 0
        while True:
            attempt += 1
            try:
                response = await client.chat.completions.create(
                    model=vision_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": SYSTEM_OCR_PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/{mime_type};base64,{b64_img}",
                                        "detail": "high",
                                    },
                                },
                            ],
                        }
                    ],
                    max_tokens=settings.ocr_max_tokens,
                )
                choice = response.choices[0]
                if getattr(choice, "finish_reason", None) == "content_filter" and not (choice.message.content or "").strip():
                    raise _ContentFiltered("finish_reason=content_filter with empty content")
                break
            except _ContentFiltered as exc:
                attempt -= 1  # not counted against the error budget below
                filtered += 1
                if filtered >= _FILTER_ATTEMPTS:
                    raise
                logger.warning("Vision OCR %d/%d: %s; retrying", filtered, _FILTER_ATTEMPTS, exc)
                await asyncio.sleep(1.0)
            except Exception as exc:  # transient gateway/rate-limit errors are common during bulk ingestion
                if attempt == _OCR_ATTEMPTS:
                    raise
                logger.warning("Vision OCR attempt %d/%d failed (%s); retrying", attempt, _OCR_ATTEMPTS, exc)
                await asyncio.sleep(2.0 * attempt)

        content = response.choices[0].message.content or ""
        cleaned = content.strip()
        if cleaned in ("---", "N/A", "none", "خالی", "None", ""):
            return ""
        return cleaned
    except Exception as exc:
        logger.warning("Vision OCR request failed for image (%s): %s", image_format, exc)
        return ""
