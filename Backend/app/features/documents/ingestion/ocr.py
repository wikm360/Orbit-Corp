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

logger = logging.getLogger(__name__)

_OCR_ATTEMPTS = 3

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


def optimize_image_for_ocr(
    image_bytes: bytes,
    max_dimension: int | None = None,
    quality: int | None = None,
) -> tuple[bytes, str]:
    """Resizes excessively large images and converts to high-quality JPEG to balance latency and OCR precision.
    Applies EXIF orientation and preserves fine decimal and tabular details."""
    settings = get_settings()
    target_max_dim = max_dimension if max_dimension is not None else getattr(settings, "ocr_max_image_dimension", 2560)
    target_quality = quality if quality is not None else getattr(settings, "ocr_jpeg_quality", 95)

    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            # 1. Apply EXIF orientation (crucial for photos/scans)
            pil_img = ImageOps.exif_transpose(pil_img)

            # 2. Handle RGBA / Palette / Transparency modes cleanly
            if pil_img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", pil_img.size, (255, 255, 255))
                if pil_img.mode == "P":
                    pil_img = pil_img.convert("RGBA")
                mask = pil_img.split()[-1] if pil_img.mode in ("RGBA", "LA") else None
                background.paste(pil_img, mask=mask)
                pil_img = background
            elif pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            # 3. Resize if dimension exceeds target_max_dim
            w, h = pil_img.size
            if max(w, h) > target_max_dim:
                scale = target_max_dim / max(w, h)
                new_size = (int(w * scale), int(h * scale))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

            # 4. Save with high JPEG quality (95) to prevent DCT compression artifacts around numbers and decimal dots
            out_buf = io.BytesIO()
            pil_img.save(out_buf, format="JPEG", quality=target_quality)
            return out_buf.getvalue(), "jpeg"
    except Exception as exc:
        logger.debug("Image optimization skipped (%s); using original bytes.", exc)
        return image_bytes, "png"


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
        # Pillow resize/encode is CPU-bound: off the event loop so other pages' requests aren't delayed behind it.
        optimized_bytes, mime_type = await asyncio.to_thread(optimize_image_for_ocr, image_bytes)
        b64_img = base64.b64encode(optimized_bytes).decode("utf-8")

        vision_model = getattr(settings, "llm_vision_model", None) or getattr(settings, "llm_model", "gpt-4o")
        client = _session_client.get() or AsyncOpenAI(
            base_url=settings.llm_api_base_url, api_key=settings.llm_api_key, timeout=_OCR_TIMEOUT
        )

        response = None
        for attempt in range(1, _OCR_ATTEMPTS + 1):
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
                break
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
