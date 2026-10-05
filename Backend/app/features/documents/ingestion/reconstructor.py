import json
import logging
from pathlib import Path

from app.features.documents.ingestion.parser import DocumentPage

logger = logging.getLogger(__name__)


def get_reconstructed_txt_path(file_path: str) -> Path:
    return Path(f"{file_path}.reconstructed.txt")


def get_reconstructed_json_path(file_path: str) -> Path:
    return Path(f"{file_path}.reconstructed.json")


def save_reconstructed_document(
    file_path: str,
    filename: str,
    pages: list[DocumentPage],
) -> tuple[str, dict]:
    """Saves the reconstructed document to disk in both human-readable text
    and machine-readable JSON formats, maintaining page-level fidelity."""
    total_pages = len(pages)
    txt_lines: list[str] = [
        f"=== مستند: {filename} ===",
        f"تعداد صفحات: {total_pages}",
        "",
    ]

    json_pages: list[dict] = []
    for page in pages:
        page_num = page.page_number
        content = page.text.strip()
        txt_lines.append(f"--- [صفحه {page_num}] ---")
        if content:
            txt_lines.append(content)
        else:
            txt_lines.append("[بدون متن]")
        txt_lines.append("")

        json_pages.append(
            {
                "page": page_num,
                "text": content,
                "has_images": len(page.images) > 0,
                "metadata": page.metadata,
            }
        )

    full_txt = "\n".join(txt_lines)

    try:
        txt_path = get_reconstructed_txt_path(file_path)
        txt_path.write_text(full_txt, encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not write reconstructed txt file %s: %s", file_path, exc)

    json_payload = {
        "filename": filename,
        "total_pages": total_pages,
        "pages": json_pages,
    }

    try:
        json_path = get_reconstructed_json_path(file_path)
        json_path.write_text(
            json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("Could not write reconstructed json file %s: %s", file_path, exc)

    return full_txt, json_payload


def load_reconstructed_document(file_path: str) -> dict | None:
    """Loads the reconstructed JSON file if present on disk."""
    json_path = get_reconstructed_json_path(file_path)
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed loading reconstructed json from %s: %s", json_path, exc)
    return None


def cleanup_reconstructed_files(file_path: str) -> None:
    """Removes reconstructed files when a source document is deleted."""
    for p in (get_reconstructed_txt_path(file_path), get_reconstructed_json_path(file_path)):
        try:
            if p.exists():
                p.unlink()
        except Exception as exc:
            logger.debug("Failed deleting reconstructed file %s: %s", p, exc)

