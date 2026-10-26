import json
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app.features.documents.ingestion.layout_helper import LayoutBlockBox
from app.features.documents.ingestion.ocr_debugger import (
    create_annotated_layout_image,
    get_debug_document_trace,
    get_debug_image_path,
    list_debug_documents,
    save_ocr_debug_artifacts,
)


def test_create_annotated_layout_image():
    img = Image.new("RGB", (800, 600), color="white")
    blocks = [
        LayoutBlockBox(x1=50, y1=30, x2=750, y2=100, block_type="header"),
        LayoutBlockBox(x1=50, y1=150, x2=750, y2=450, block_type="table"),
        LayoutBlockBox(x1=50, y1=500, x2=750, y2=580, block_type="footer"),
    ]
    annotated = create_annotated_layout_image(img, blocks)
    assert annotated.size == (800, 600)
    assert annotated.mode == "RGB"


def test_save_and_retrieve_ocr_debug_artifacts(tmp_path):
    img = Image.new("RGB", (400, 400), color="white")
    blocks = [
        LayoutBlockBox(x1=20, y1=20, x2=200, y2=100, block_type="header"),
        LayoutBlockBox(x1=20, y1=120, x2=380, y2=350, block_type="table"),
    ]
    block_results = [
        {"text": "عنوان سند", "duration_ms": 120.0},
        {"text": "| A | B |\n| 1 | 2 |", "duration_ms": 450.0},
    ]

    doc_id = "test-doc-123"

    with patch("app.features.documents.ingestion.ocr_debugger.get_settings") as mock_settings:
        mock_settings.return_value.upload_dir = str(tmp_path)

        saved_dir = save_ocr_debug_artifacts(
            document_id=doc_id,
            page_number=1,
            pil_img=img,
            blocks=blocks,
            block_results=block_results,
            final_text="عنوان سند\n\n| A | B |\n| 1 | 2 |",
            total_duration_ms=600.0,
            mistral_duration_ms=250.0,
        )
        assert saved_dir is not None
        assert (saved_dir / "page_1_annotated.png").exists()
        assert (saved_dir / "page_1_crop_01_header.png").exists()
        assert (saved_dir / "page_1_crop_02_table.png").exists()
        assert (saved_dir / "debug_trace.json").exists()

        # Test listing
        doc_list = list_debug_documents()
        assert len(doc_list) == 1
        assert doc_list[0]["document_id"] == doc_id
        assert doc_list[0]["pages_count"] == 1

        # Test trace retrieval
        trace = get_debug_document_trace(doc_id)
        assert trace is not None
        assert "pages" in trace
        assert "1" in trace["pages"]
        assert trace["pages"]["1"]["blocks_count"] == 2

        # Test image path resolution & path traversal safety
        valid_path = get_debug_image_path(doc_id, "page_1_annotated.png")
        assert valid_path is not None
        assert valid_path.exists()

        # Path traversal must be rejected
        invalid_path = get_debug_image_path(doc_id, "../../../etc/passwd")
        assert invalid_path is None

