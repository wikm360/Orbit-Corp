"""Finds the rotation that makes a scanned page upright (0/90/180/270). Three methods (`OCR_ORIENT_METHOD`):

- `osd`: Tesseract's orientation detection - local, ~0.6 s of CPU, no API call.
- `model`: a cheap low-resolution question to the vision model.
- `hybrid` (default): OSD first; the model only confirms a proposed rotation or decides when OSD is unsure.

Measured on four real scans rotated by 0/90/180/270 plus 24 PDF pages (64 cases, `.agents/ops/ocr-preprocessing-evaluation.md`):
- the vision model (gemini-flash-lite) reliably says *whether* a page is upright but often names the wrong *direction*
  (90 for a page that needed 270), so every rotation it proposes is checked by asking again about the rotated image;
- Tesseract OSD got 60/64 when the image is large enough (~300 dpi: long side upscaled to 2400 px; at 100 dpi it
  failed on most pages). Its mistakes are asymmetric: calling a rotated page "upright" leaves it as it was, but calling an
  upright page "rotated" damages it - so in `hybrid` a rotation proposed by OSD is confirmed by the model before use.
"""

import asyncio
import io
import logging
import os
import re
import shutil
import subprocess
import threading
from collections.abc import Awaitable, Callable

from PIL import Image

logger = logging.getLogger(__name__)

PROBE_SIDE = 768  # long side of the thumbnail sent with the probe (~1.1k input tokens)

PROBE_PROMPT = (
    "This is a scanned document page. Is the text upright, i.e. in normal reading orientation? "
    "If not, say how many degrees the page must be rotated CLOCKWISE to become upright. "
    'Answer with exactly one JSON object: {"rotate_clockwise": 0|90|180|270}.'
)
_ANSWER = re.compile(r'"rotate_clockwise"\s*:\s*(0|90|180|270)')

Probe = Callable[[Image.Image], Awaitable[int | None]]
OsdDetect = Callable[[Image.Image], Awaitable[tuple[int | None, float]]]

ORIENT_METHODS = ("model", "osd", "hybrid")
OSD_TARGET_SIDE = 2400  # Tesseract needs ~300 dpi; smaller images are upscaled to this long side (A4 at 200 dpi is ~2300)
OSD_MAX_SIDE = 3200  # larger images are downscaled: OSD time grows with the area and gains nothing
OSD_TIMEOUT_SECONDS = 30
_OSD_ROTATE = re.compile(r"Rotate:\s*(\d+)")
_OSD_CONFIDENCE = re.compile(r"Orientation confidence:\s*([\d.]+)")


def parse_probe_answer(text: str) -> int | None:
    match = _ANSWER.search(text or "")
    return int(match.group(1)) if match else None


def probe_thumbnail(image: Image.Image) -> Image.Image:
    thumb = image.convert("RGB")
    thumb.thumbnail((PROBE_SIDE, PROBE_SIDE), Image.Resampling.BILINEAR)
    return thumb


def rotate_clockwise(image: Image.Image, degrees: int) -> Image.Image:
    return image.rotate(-degrees, expand=True, fillcolor=(255, 255, 255)) if degrees else image


async def find_upright_rotation(image: Image.Image, probe: Probe) -> int:
    """Degrees to rotate `image` clockwise to make it upright (0 = leave it alone). Never raises: any probe failure
    means "do not rotate"."""
    thumb = probe_thumbnail(image)
    try:
        first = await probe(thumb)
        if first in (None, 0):
            return 0
        candidates = [first] + [d for d in (90, 270, 180) if d != first]
        answers = await asyncio.gather(*(probe(rotate_clockwise(thumb, d)) for d in candidates))
    except Exception:
        return 0
    for degrees, answer in zip(candidates, answers):
        if answer == 0:  # the first such candidate is the model's own hint when it was right
            return degrees
    return 0


# ---- Tesseract OSD

_osd_slots: threading.BoundedSemaphore | None = None
_osd_missing_logged = False


def parse_osd_output(stdout: str) -> tuple[int | None, float]:
    """(clockwise degrees to make the page upright, confidence) from `tesseract --psm 0` output; (None, 0) if unusable."""
    rotate = _OSD_ROTATE.search(stdout or "")
    confidence = _OSD_CONFIDENCE.search(stdout or "")
    if not rotate or int(rotate.group(1)) not in (0, 90, 180, 270):
        return None, 0.0
    return int(rotate.group(1)), float(confidence.group(1)) if confidence else 0.0


def _osd_png(image: Image.Image) -> bytes:
    gray = image.convert("L")
    longest = max(gray.size)
    if longest < OSD_TARGET_SIDE or longest > OSD_MAX_SIDE:
        scale = OSD_TARGET_SIDE / longest
        gray = gray.resize((max(1, int(gray.width * scale)), max(1, int(gray.height * scale))), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    gray.save(buf, format="PNG", compress_level=1)
    return buf.getvalue()


def _run_osd(image: Image.Image, concurrency: int) -> tuple[int | None, float]:
    global _osd_slots, _osd_missing_logged
    binary = shutil.which("tesseract")
    if binary is None:
        if not _osd_missing_logged:
            _osd_missing_logged = True
            logger.warning("tesseract is not installed: orientation detection falls back to the vision model.")
        return None, 0.0
    if _osd_slots is None:  # a process-wide limit: every ingestion job has its own event loop, so an asyncio lock won't do
        _osd_slots = threading.BoundedSemaphore(max(1, concurrency))
    payload = _osd_png(image)
    with _osd_slots:
        try:
            result = subprocess.run(
                [binary, "stdin", "stdout", "--psm", "0", "-l", "osd"],
                input=payload,
                capture_output=True,
                timeout=OSD_TIMEOUT_SECONDS,
                env={**os.environ, "OMP_THREAD_LIMIT": "1"},  # several pages run at once: one thread per process
            )
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("tesseract OSD failed (%s)", exc)
            return None, 0.0
    return parse_osd_output(result.stdout.decode("utf-8", errors="ignore"))


async def detect_rotation_osd(image: Image.Image, concurrency: int = 4) -> tuple[int | None, float]:
    """Clockwise rotation proposed by Tesseract OSD and its confidence; (None, 0.0) when it cannot tell (too little
    text, tesseract missing, timeout)."""
    return await asyncio.to_thread(_run_osd, image, concurrency)


async def choose_rotation(
    image: Image.Image,
    *,
    method: str,
    probe: Probe,
    osd: OsdDetect,
    min_confidence: float,
) -> int:
    """Clockwise degrees to rotate `image` so it is upright, by the configured method (never raises)."""
    if method == "model":
        return await find_upright_rotation(image, probe)
    try:
        degrees, confidence = await osd(image)
    except Exception:  # noqa: BLE001
        degrees, confidence = None, 0.0
    if degrees is not None and confidence >= min_confidence:
        if degrees == 0 or method == "osd":
            return degrees
        # hybrid: a proposed rotation is only used if the model agrees the rotated page is upright
        try:
            if await probe(probe_thumbnail(rotate_clockwise(image, degrees))) == 0:
                return degrees
        except Exception:  # noqa: BLE001
            pass
        logger.info("OSD proposed %d degrees (confidence %.1f) but the model disagreed; asking the model.", degrees, confidence)
    elif method == "osd":
        return 0  # unsure and no model fallback requested: leave the page as it is
    return await find_upright_rotation(image, probe)
