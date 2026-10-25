from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
import io
import logging
from typing import Sequence

from PIL import Image

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LayoutBlockBox:
    """Bounding box coordinates [x1, y1, x2, y2] and block type on the target image."""

    x1: int
    y1: int
    x2: int
    y2: int
    block_type: str = "text"

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    @property
    def area(self) -> int:
        return self.width * self.height


# Backward-compatible alias
TableBoundingBox = LayoutBlockBox


@dataclass
class DocumentLayoutResult:
    """Layout analysis result containing all content bounding boxes and separated table boxes."""

    blocks: list[LayoutBlockBox] = field(default_factory=list)
    table_boxes: list[LayoutBlockBox] = field(default_factory=list)
    header_text: str = ""
    footer_text: str = ""
    pre_table_text: str = ""
    post_table_text: str = ""

    def __iter__(self):
        return iter(self.blocks or self.table_boxes)

    def __len__(self):
        return len(self.blocks or self.table_boxes)

    def __bool__(self):
        return bool(self.blocks or self.table_boxes)

    def __getitem__(self, index):
        return (self.blocks or self.table_boxes)[index]

    def __eq__(self, other):
        if isinstance(other, list):
            return self.table_boxes == other or self.blocks == other
        if isinstance(other, DocumentLayoutResult):
            return (
                self.table_boxes == other.table_boxes
                and self.blocks == other.blocks
                and self.header_text == other.header_text
                and self.footer_text == other.footer_text
                and self.pre_table_text == other.pre_table_text
                and self.post_table_text == other.post_table_text
            )
        return False


def _blocks_can_merge(b1: LayoutBlockBox, b2: LayoutBlockBox, margin_y: int = 35, margin_x: int = 60) -> bool:
    """Checks if two blocks should be merged. Tables only merge with tables; text only with text."""
    is_t1 = b1.block_type == "table"
    is_t2 = b2.block_type == "table"
    if is_t1 != is_t2:
        return False

    v_overlap = not (b1.y2 + margin_y < b2.y1 or b2.y2 + margin_y < b1.y1)
    if not v_overlap:
        return False

    h_overlap = not (b1.x2 + margin_x < b2.x1 or b2.x2 + margin_x < b1.x1)
    return h_overlap


def merge_layout_blocks(
    blocks: Sequence[LayoutBlockBox],
    margin_y: int = 35,
    margin_x: int = 60,
) -> list[LayoutBlockBox]:
    """Combines overlapping or vertically/horizontally adjacent layout blocks into logical sections."""
    if not blocks:
        return []

    remaining = sorted(blocks, key=lambda b: (b.y1, b.x1))
    merged: list[LayoutBlockBox] = []

    while remaining:
        current = remaining.pop(0)
        changed = True
        while changed:
            changed = False
            uncombined = []
            for other in remaining:
                if _blocks_can_merge(current, other, margin_y=margin_y, margin_x=margin_x):
                    current = LayoutBlockBox(
                        x1=min(current.x1, other.x1),
                        y1=min(current.y1, other.y1),
                        x2=max(current.x2, other.x2),
                        y2=max(current.y2, other.y2),
                        block_type=current.block_type,
                    )
                    changed = True
                else:
                    uncombined.append(other)
            remaining = uncombined
        merged.append(current)

    return sorted(merged, key=lambda b: (b.y1, b.x1))


def merge_table_boxes(boxes: Sequence[LayoutBlockBox], margin: int = 40) -> list[LayoutBlockBox]:
    """Combines overlapping or adjacent table bounding boxes into single enclosing boxes."""
    return merge_layout_blocks(boxes, margin_y=margin, margin_x=margin)


def _encode_for_layout_analysis(pil_img: Image.Image, max_dim: int = 1600) -> str:
    """Encodes a moderately sized JPEG for layout analysis to avoid large network payloads."""
    img = pil_img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _call_mistral_ocr_sync(api_key: str, model: str, b64_img: str, timeout_ms: int):
    """Synchronous Mistral OCR call executed in a worker thread."""
    from mistralai.client import Mistral

    client = Mistral(api_key=api_key)
    return client.ocr.process(
        model=model,
        document={"type": "image_url", "image_url": f"data:image/jpeg;base64,{b64_img}"},
        include_blocks=True,
        timeout_ms=timeout_ms,
    )


async def detect_tables_with_mistral(
    image: Image.Image | bytes,
    padding: int = 30,
) -> DocumentLayoutResult:
    """Detects table boundaries and surrounding header/footer metadata using Mistral OCR.

    Returns a DocumentLayoutResult containing TableBoundingBox items and surrounding text.
    If Mistral is disabled, the API key is not configured, no tables are detected, or any
    network/API error occurs, gracefully returns an empty DocumentLayoutResult (triggering fallback).
    """
    settings = get_settings()
    if not getattr(settings, "ocr_two_stage_enabled", True):
        return DocumentLayoutResult()

    api_key = getattr(settings, "effective_mistral_api_key", "") or getattr(settings, "mistral_api_key", "") or getattr(settings, "mistral_key", "")
    if not api_key:
        logger.debug("Mistral API key not configured; skipping two-stage table detection.")
        return DocumentLayoutResult()

    try:
        if isinstance(image, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(image))
        else:
            pil_img = image

        orig_w, orig_h = pil_img.size
        if orig_w < 100 or orig_h < 100:
            return DocumentLayoutResult()

        b64_img = await asyncio.to_thread(_encode_for_layout_analysis, pil_img)
        model = getattr(settings, "mistral_ocr_model", "mistral-ocr-latest")
        timeout_sec = float(getattr(settings, "mistral_ocr_timeout_seconds", 25.0))
        timeout_ms = int(timeout_sec * 1000)

        response = await asyncio.wait_for(
            asyncio.to_thread(_call_mistral_ocr_sync, api_key, model, b64_img, timeout_ms),
            timeout=timeout_sec + 2.0,
        )

        pages = getattr(response, "pages", None) or []
        if not pages:
            return DocumentLayoutResult()

        page = pages[0]
        ref_dims = getattr(page, "dimensions", None)
        if not ref_dims or not getattr(ref_dims, "width", None) or not getattr(ref_dims, "height", None):
            return DocumentLayoutResult()

        scale_x = orig_w / ref_dims.width
        scale_y = orig_h / ref_dims.height

        blocks = getattr(page, "blocks", None) or []
        all_raw_boxes: list[LayoutBlockBox] = []
        table_raw_boxes: list[LayoutBlockBox] = []

        for block in blocks:
            b_type = (getattr(block, "type", "") or "text").lower()
            tl_x = getattr(block, "top_left_x", None)
            tl_y = getattr(block, "top_left_y", None)
            br_x = getattr(block, "bottom_right_x", None)
            br_y = getattr(block, "bottom_right_y", None)
            if None in (tl_x, tl_y, br_x, br_y):
                continue

            pad = padding if b_type == "table" else max(15, padding // 2)
            x1 = max(0, int(tl_x * scale_x) - pad)
            y1 = max(0, int(tl_y * scale_y) - pad)
            x2 = min(orig_w, int(br_x * scale_x) + pad)
            y2 = min(orig_h, int(br_y * scale_y) + pad)

            if x2 > x1 + 10 and y2 > y1 + 10:
                box = LayoutBlockBox(x1=x1, y1=y1, x2=x2, y2=y2, block_type=b_type)
                all_raw_boxes.append(box)
                if b_type == "table":
                    table_raw_boxes.append(box)

        # Merge adjacent blocks into cohesive reading sections
        merged_all = merge_layout_blocks(all_raw_boxes, margin_y=35, margin_x=60)
        merged_tables = [b for b in merged_all if b.block_type == "table"]
        if not merged_tables and table_raw_boxes:
            merged_tables = merge_table_boxes(table_raw_boxes, margin=padding)

        header_text = (getattr(page, "header", "") or "").strip()
        footer_text = (getattr(page, "footer", "") or "").strip()
        pre_blocks: list[str] = []
        post_blocks: list[str] = []

        if merged_tables:
            min_table_y = min(b.y1 for b in merged_tables)
            max_table_y = max(b.y2 for b in merged_tables)

            for block in blocks:
                b_type = (getattr(block, "type", "") or "").lower()
                if b_type != "table":
                    content = (getattr(block, "content", "") or "").strip()
                    if not content:
                        continue
                    b_tl_y = int(getattr(block, "top_left_y", 0) * scale_y)
                    b_br_y = int(getattr(block, "bottom_right_y", 0) * scale_y)
                    if b_br_y <= min_table_y + padding:
                        pre_blocks.append(content)
                    elif b_tl_y >= max_table_y - padding:
                        post_blocks.append(content)

            logger.info(
                "Mistral layout analysis detected %d block(s) (%d table(s)) on image (%dx%d).",
                len(merged_all),
                len(merged_tables),
                orig_w,
                orig_h,
            )
        elif merged_all:
            logger.info("Mistral layout analysis detected %d content block(s) on image (%dx%d).", len(merged_all), orig_w, orig_h)

        return DocumentLayoutResult(
            blocks=merged_all,
            table_boxes=merged_tables,
            header_text=header_text,
            footer_text=footer_text,
            pre_table_text="\n\n".join(pre_blocks),
            post_table_text="\n\n".join(post_blocks),
        )

    except asyncio.TimeoutError:
        logger.warning("Mistral OCR layout detection timed out after %.1fs; falling back to full-page vision OCR.", timeout_sec)
        return DocumentLayoutResult()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Mistral OCR layout detection failed (%s); falling back to full-page vision OCR.", exc)
        return DocumentLayoutResult()


def crop_image_box(pil_img: Image.Image, box: TableBoundingBox) -> Image.Image:
    """Crops a region from the PIL Image according to the TableBoundingBox."""
    return pil_img.crop((box.x1, box.y1, box.x2, box.y2))
