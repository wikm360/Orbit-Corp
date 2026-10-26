from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings
from app.features.documents.ingestion.layout_helper import LayoutBlockBox

logger = logging.getLogger(__name__)

# Colors for bounding box annotations (RGB)
_COLOR_PALETTE: dict[str, tuple[int, int, int]] = {
    "table": (239, 68, 68),       # Red
    "header": (59, 130, 246),     # Blue
    "title": (147, 51, 234),      # Purple
    "text": (34, 197, 94),        # Green
    "paragraph": (34, 197, 94),   # Green
    "footer": (249, 115, 22),     # Orange
}
_DEFAULT_COLOR = (107, 114, 128)  # Gray


def _get_color_for_type(block_type: str) -> tuple[int, int, int]:
    return _COLOR_PALETTE.get(block_type.lower(), _DEFAULT_COLOR)


def create_annotated_layout_image(
    pil_img: Image.Image,
    blocks: Sequence[LayoutBlockBox],
) -> Image.Image:
    """Draws colored bounding boxes and informative labels on a copy of the image."""
    annotated = pil_img.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for idx, b in enumerate(blocks, 1):
        color = _get_color_for_type(b.block_type)
        # Draw bounding rectangle
        draw.rectangle([b.x1, b.y1, b.x2, b.y2], outline=color, width=4)

        # Label tag
        label = f" #{idx} [{b.block_type.upper()}] {b.width}x{b.height} "
        label_y = max(0, b.y1 - 22) if b.y1 >= 22 else b.y1 + 4
        # Calculate text width approximately if getbbox not supported
        try:
            bbox = font.getbbox(label) if font else None
            text_w = (bbox[2] - bbox[0]) if bbox else len(label) * 8
            text_h = (bbox[3] - bbox[1]) if bbox else 16
        except Exception:
            text_w = len(label) * 8
            text_h = 16

        badge_x2 = min(annotated.width, b.x1 + text_w + 6)
        badge_y2 = label_y + text_h + 4

        # Draw badge background pill and text
        draw.rectangle([b.x1, label_y, badge_x2, badge_y2], fill=color)
        draw.text((b.x1 + 3, label_y + 2), label, fill=(255, 255, 255), font=font)

    return annotated


def get_debug_dir(document_id: str | None = None) -> Path:
    """Returns the persistent debug directory for OCR traces."""
    settings = get_settings()
    base_dir = Path(settings.upload_dir) / "debug_ocr"
    if document_id:
        return base_dir / str(document_id)
    return base_dir


def save_ocr_debug_artifacts(
    document_id: str,
    page_number: int,
    pil_img: Image.Image,
    blocks: Sequence[LayoutBlockBox],
    block_results: list[dict[str, Any]],
    final_text: str,
    total_duration_ms: float = 0.0,
    mistral_duration_ms: float = 0.0,
) -> Path | None:
    """Saves annotated page image, individual cropped blocks, and debug trace JSON.
    Guarantees no exceptions bubble up to fail the document ingestion."""
    try:
        target_dir = get_debug_dir(document_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save annotated image with bounding boxes
        annotated = create_annotated_layout_image(pil_img, blocks)
        annotated_filename = f"page_{page_number}_annotated.png"
        annotated.save(target_dir / annotated_filename, format="PNG")

        # 2. Save individual crop images
        saved_crops_info: list[dict[str, Any]] = []
        for idx, (b, res) in enumerate(zip(blocks, block_results, strict=False), 1):
            crop_filename = f"page_{page_number}_crop_{idx:02d}_{b.block_type}.png"
            try:
                cropped = pil_img.crop((b.x1, b.y1, b.x2, b.y2))
                cropped.save(target_dir / crop_filename, format="PNG")
            except Exception as crop_err:
                logger.debug("Failed saving crop image %s: %s", crop_filename, crop_err)

            saved_crops_info.append({
                "block_index": idx,
                "block_type": b.block_type,
                "box": [b.x1, b.y1, b.x2, b.y2],
                "width": b.width,
                "height": b.height,
                "crop_image": crop_filename,
                "text": res.get("text", ""),
                "duration_ms": res.get("duration_ms", 0),
            })

        # 3. Update master trace JSON
        trace_path = target_dir / "debug_trace.json"
        master_trace: dict[str, Any] = {
            "document_id": str(document_id),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "pages": {},
        }
        if trace_path.exists():
            try:
                with open(trace_path, encoding="utf-8") as f:
                    master_trace = json.load(f)
            except Exception:
                pass

        master_trace["updated_at"] = datetime.now(timezone.utc).isoformat()
        pages = master_trace.setdefault("pages", {})
        pages[str(page_number)] = {
            "page_number": page_number,
            "width": pil_img.width,
            "height": pil_img.height,
            "annotated_image": annotated_filename,
            "mistral_duration_ms": round(mistral_duration_ms, 1),
            "total_duration_ms": round(total_duration_ms, 1),
            "blocks_count": len(saved_crops_info),
            "blocks": saved_crops_info,
            "final_text": final_text,
        }

        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(master_trace, f, ensure_ascii=False, indent=2)

        return target_dir
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed saving OCR debug artifacts for doc %s page %d: %s", document_id, page_number, exc)
        return None


def list_debug_documents() -> list[dict[str, Any]]:
    """Lists all documents that have debug OCR traces recorded."""
    base_dir = get_debug_dir()
    if not base_dir.exists():
        return []

    docs = []
    for entry in base_dir.iterdir():
        if entry.is_dir():
            trace_path = entry / "debug_trace.json"
            if trace_path.exists():
                try:
                    with open(trace_path, encoding="utf-8") as f:
                        data = json.load(f)
                        pages = data.get("pages", {})
                        docs.append({
                            "document_id": entry.name,
                            "updated_at": data.get("updated_at", ""),
                            "pages_count": len(pages),
                            "pages": sorted([int(p) for p in pages.keys()]),
                        })
                except Exception:
                    docs.append({
                        "document_id": entry.name,
                        "updated_at": "",
                        "pages_count": 0,
                        "pages": [],
                    })
    # Sort descending by updated_at
    docs.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
    return docs


def get_debug_document_trace(document_id: str) -> dict[str, Any] | None:
    """Retrieves the full debug trace JSON for a document."""
    trace_path = get_debug_dir(document_id) / "debug_trace.json"
    if not trace_path.exists():
        return None
    try:
        with open(trace_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed reading debug trace for doc %s: %s", document_id, exc)
        return None


def get_debug_image_path(document_id: str, filename: str) -> Path | None:
    """Safely retrieves the path to a debug image, guarding against directory traversal."""
    doc_dir = get_debug_dir(document_id).resolve()
    target_path = (doc_dir / filename).resolve()
    # Path traversal check
    if not str(target_path).startswith(str(doc_dir)):
        return None
    if not target_path.exists() or not target_path.is_file():
        return None
    return target_path

