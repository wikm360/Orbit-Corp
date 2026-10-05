import base64
import io
import logging

from openai import AsyncOpenAI
from PIL import Image

from app.core.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_OCR_PROMPT = (
    "شما یک موتور قدرتمند OCR و تحلیل تصویر اسناد هستید.\n"
    "وظیفه شما رونویسی و استخراج دقیق تمام متون، ارقام، جداول، دست‌نوشته‌ها و دیاگرام‌های موجود در این تصویر است.\n\n"
    "دستورالعمل‌ها:\n"
    "۱. تمام متن‌ها و عبارات را دقیقاً، با حفظ زبان (فارسی، انگلیسی یا هر زبان دیگر) و ترتیب منطقی استخراج کنید.\n"
    "۲. اگر در تصویر جدول وجود دارد، ساختار آن را دقیقاً به جدول مارک‌داون (Markdown Table) تبدیل کنید.\n"
    "۳. اگر تصویر نمودار، فلوچارت، فرم، یا دیاگرام است، علاوه بر متون آن، توضیحی فشرده و دقیق از ساختار، ارقام و روابط آن بنویسید.\n"
    "۴. اگر تصویر هیچ متن یا اطلاعات معناداری ندارد (مثلا فقط یک خط تیره، حاشیه خالی، آیکون ساده یا نویز است)، خروجی باید یک رشته خالی باشد.\n"
    "۵. خروجی فقط و فقط باید محتوای استخراج شده باشد؛ از اضافه کردن هرگونه سلام، توضیح مقدماتی یا نتیجه‌گیری خودداری کنید."
)


def optimize_image_for_ocr(image_bytes: bytes, max_dimension: int = 2048) -> tuple[bytes, str]:
    """Resizes excessively large images and converts to clean JPEG to balance latency and accuracy."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            # Handle RGBA / Palette / Transparency modes
            if pil_img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", pil_img.size, (255, 255, 255))
                if pil_img.mode == "P":
                    pil_img = pil_img.convert("RGBA")
                mask = pil_img.split()[-1] if pil_img.mode in ("RGBA", "LA") else None
                background.paste(pil_img, mask=mask)
                pil_img = background
            elif pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            w, h = pil_img.size
            if max(w, h) > max_dimension:
                scale = max_dimension / max(w, h)
                new_size = (int(w * scale), int(h * scale))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

            out_buf = io.BytesIO()
            pil_img.save(out_buf, format="JPEG", quality=85)
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
        optimized_bytes, mime_type = optimize_image_for_ocr(image_bytes)
        b64_img = base64.b64encode(optimized_bytes).decode("utf-8")

        vision_model = getattr(settings, "llm_vision_model", None) or getattr(settings, "llm_model", "gpt-4o")
        client = AsyncOpenAI(base_url=settings.llm_api_base_url, api_key=settings.llm_api_key)

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
            max_tokens=2048,
        )

        content = response.choices[0].message.content or ""
        cleaned = content.strip()
        if cleaned in ("---", "N/A", "none", "خالی", "None", ""):
            return ""
        return cleaned
    except Exception as exc:
        logger.warning("Vision OCR request failed for image (%s): %s", image_format, exc)
        return ""

