"""Pure-Pillow/numpy image clean-up applied before an image is sent to the vision-OCR model.

Every step is a function `Image -> Image` (or a measurement) so the steps can be evaluated one by one
(`tools/ocr_eval/`). Nothing here talks to the network.
"""

import numpy as np
from PIL import Image, ImageFilter, ImageOps

_ANALYSIS_SIDE = 1200  # skew/crop analysis runs on a thumbnail, never on the full-size page


def _ink_mask(gray: Image.Image) -> np.ndarray:
    """Boolean mask of dark (ink) pixels, using a threshold between the page background and the darkest strokes."""
    arr = np.asarray(gray, dtype=np.float32)
    background = np.percentile(arr, 90)
    darkest = np.percentile(arr, 2)
    if background - darkest < 25:  # no usable contrast: blank page or flat photo
        return np.zeros(arr.shape, dtype=bool)
    return arr < (background + darkest) / 2


def _thumbnail(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    gray.thumbnail((_ANALYSIS_SIDE, _ANALYSIS_SIDE), Image.Resampling.BILINEAR)
    return gray


def ink_ratio(image: Image.Image, drop: float = 35.0) -> float:
    """Fraction of pixels clearly different from the page background (median; dark or light ink) - ~0 for a blank page, even a noisy/grey one.
    Absolute threshold on purpose: a faint scan still has strokes 40+ levels below its background, while the
    contrast-relative mask used for skew/crop would call a washed-out page empty."""
    gray = np.asarray(_thumbnail(image), dtype=np.float32)
    return float((np.abs(gray - np.median(gray)) > drop).mean())


def is_blank(image: Image.Image, min_ink_ratio: float = 0.002) -> bool:
    """True for a page with no content. Real pages measured 0.036 and up (a sparse letter), a blank scan 0.0."""
    return ink_ratio(image) < min_ink_ratio


def _row_sharpness(mask: np.ndarray, angle: float) -> float:
    rotated = Image.fromarray(mask.astype(np.uint8) * 255).rotate(angle, resample=Image.Resampling.BILINEAR)
    rows = np.asarray(rotated, dtype=np.float32).sum(axis=1)
    diff = np.diff(rows)
    return float((diff * diff).sum())


def estimate_skew(image: Image.Image, max_angle: float = 8.0) -> float:
    """Skew of the text lines in degrees (positive = needs a counter-clockwise rotation to straighten).
    Projection-profile search: the right angle is the one where text lines/table rules form the sharpest row profile."""
    mask = _ink_mask(_thumbnail(image))
    if not mask.any():
        return 0.0
    coarse = np.arange(-max_angle, max_angle + 0.01, 0.5)
    best = max(coarse, key=lambda a: _row_sharpness(mask, float(a)))
    fine = np.arange(best - 0.5, best + 0.51, 0.1)
    best = max(fine, key=lambda a: _row_sharpness(mask, float(a)))
    # a flat profile (photo, no lines) must not produce a random rotation
    if _row_sharpness(mask, float(best)) < 1.05 * _row_sharpness(mask, 0.0):
        return 0.0
    return float(best)


def deskew(image: Image.Image, min_angle: float = 0.4, max_angle: float = 8.0) -> Image.Image:
    angle = estimate_skew(image, max_angle)
    if abs(angle) < min_angle:
        return image
    fill = (255, 255, 255) if image.mode == "RGB" else 255
    return image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=fill)


def crop_margins(image: Image.Image, padding_ratio: float = 0.02, min_kept_ratio: float = 0.3) -> Image.Image:
    """Crops the empty (or scanner-black) border around the content. Keeps the page if the box would drop too much."""
    thumb = _thumbnail(image)
    mask = _ink_mask(thumb)
    if not mask.any():
        return image
    # ignore stray specks: a row/column counts only if it has a few ink pixels
    rows = np.where(mask.sum(axis=1) >= 3)[0]
    cols = np.where(mask.sum(axis=0) >= 3)[0]
    if rows.size == 0 or cols.size == 0:
        return image
    scale_x = image.width / thumb.width
    scale_y = image.height / thumb.height
    pad_x = int(image.width * padding_ratio)
    pad_y = int(image.height * padding_ratio)
    left = max(0, int(cols[0] * scale_x) - pad_x)
    right = min(image.width, int((cols[-1] + 1) * scale_x) + pad_x)
    top = max(0, int(rows[0] * scale_y) - pad_y)
    bottom = min(image.height, int((rows[-1] + 1) * scale_y) + pad_y)
    kept = (right - left) * (bottom - top) / (image.width * image.height)
    if kept < min_kept_ratio or kept > 0.97:
        return image
    return image.crop((left, top, right, bottom))


def normalize_background(image: Image.Image, blur_ratio: float = 0.04) -> Image.Image:
    """Divides the page by its blurred self: removes shadows/uneven lighting, then stretches the contrast."""
    gray = image.convert("L")
    small = gray.copy()
    small.thumbnail((600, 600), Image.Resampling.BILINEAR)
    radius = max(5, int(max(small.size) * blur_ratio))
    background = small.filter(ImageFilter.GaussianBlur(radius)).resize(gray.size, Image.Resampling.BILINEAR)
    page = np.asarray(gray, dtype=np.float32)
    bg = np.maximum(np.asarray(background, dtype=np.float32), 1.0)
    flat = np.clip(page / bg * 255.0, 0, 255).astype(np.uint8)
    return ImageOps.autocontrast(Image.fromarray(flat), cutoff=0.5).convert("RGB")


def enhance_contrast(image: Image.Image, cutoff: float = 1.0) -> Image.Image:
    """Global auto-contrast (clips `cutoff` percent of the darkest/lightest pixels)."""
    return ImageOps.autocontrast(image.convert("RGB"), cutoff=cutoff)


def split_vertical(image: Image.Image, parts: int = 2, overlap_ratio: float = 0.08) -> list[Image.Image]:
    """Splits a tall page into `parts` horizontal bands with overlap (each band is OCR'd separately)."""
    height = image.height
    band = height / parts
    overlap = int(height * overlap_ratio)
    out = []
    for i in range(parts):
        top = max(0, int(i * band) - (overlap if i else 0))
        bottom = min(height, int((i + 1) * band) + (overlap if i < parts - 1 else 0))
        out.append(image.crop((0, top, image.width, bottom)))
    return out
