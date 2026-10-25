import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.core.config import get_settings
from app.features.documents.ingestion import ocr as ocr_module
from app.features.documents.ingestion.layout_helper import (
    DocumentLayoutResult,
    TableBoundingBox,
    crop_image_box,
    detect_tables_with_mistral,
    merge_table_boxes,
)


def test_merge_table_boxes():
    b1 = TableBoundingBox(x1=10, y1=10, x2=100, y2=100)
    b2 = TableBoundingBox(x1=80, y1=80, x2=200, y2=200)  # overlaps b1
    b3 = TableBoundingBox(x1=400, y1=400, x2=500, y2=500)  # far away

    merged = merge_table_boxes([b1, b2, b3], margin=20)
    assert len(merged) == 2

    # First box should enclose b1 and b2
    enclosing = next(b for b in merged if b.x1 == 10)
    assert enclosing.x1 == 10
    assert enclosing.y1 == 10
    assert enclosing.x2 == 200
    assert enclosing.y2 == 200

    isolated = next(b for b in merged if b.x1 == 400)
    assert isolated.x1 == 400
    assert isolated.x2 == 500


def test_crop_image_box():
    img = Image.new("RGB", (500, 500), color="blue")
    box = TableBoundingBox(x1=50, y1=60, x2=250, y2=360)
    cropped = crop_image_box(img, box)
    assert cropped.size == (200, 300)


@pytest.mark.asyncio
async def test_detect_tables_with_mistral_disabled():
    img = Image.new("RGB", (400, 400), color="white")
    with patch("app.features.documents.ingestion.layout_helper.get_settings") as mock_settings:
        mock_settings.return_value.ocr_two_stage_enabled = False
        mock_settings.return_value.effective_mistral_api_key = "test-key"
        boxes = await detect_tables_with_mistral(img)
        assert boxes == []

    with patch("app.features.documents.ingestion.layout_helper.get_settings") as mock_settings:
        mock_settings.return_value.ocr_two_stage_enabled = True
        mock_settings.return_value.effective_mistral_api_key = ""
        boxes = await detect_tables_with_mistral(img)
        assert boxes == []


@pytest.mark.asyncio
async def test_detect_tables_with_mistral_success():
    # 2000x3000 target image
    img = Image.new("RGB", (2000, 3000), color="white")

    # Mock Mistral OCR response where reference dimensions are 1000x1500 (scale factor = 2.0)
    mock_block = SimpleNamespace(
        type="table",
        top_left_x=100,
        top_left_y=200,
        bottom_right_x=400,
        bottom_right_y=600,
    )
    mock_header_block = SimpleNamespace(
        type="header",
        top_left_x=100,
        top_left_y=50,
        bottom_right_x=400,
        bottom_right_y=150,
    )
    mock_page = SimpleNamespace(
        dimensions=SimpleNamespace(width=1000, height=1500),
        blocks=[mock_header_block, mock_block],
    )
    mock_resp = SimpleNamespace(pages=[mock_page])

    with (
        patch("app.features.documents.ingestion.layout_helper.get_settings") as mock_settings,
        patch("app.features.documents.ingestion.layout_helper._call_mistral_ocr_sync", return_value=mock_resp),
    ):
        mock_settings.return_value.ocr_two_stage_enabled = True
        mock_settings.return_value.effective_mistral_api_key = "test-key"
        mock_settings.return_value.mistral_ocr_model = "mistral-ocr-latest"
        mock_settings.return_value.mistral_ocr_timeout_seconds = 10.0

        layout_res = await detect_tables_with_mistral(img, padding=30)
        assert len(layout_res.table_boxes) == 1
        assert len(layout_res.blocks) == 2
        box = layout_res.table_boxes[0]

        # scale = 2.0
        # raw x1=100*2 = 200 - 30 = 170
        # raw y1=200*2 = 400 - 30 = 370
        # raw x2=400*2 = 800 + 30 = 830
        # raw y2=600*2 = 1200 + 30 = 1230
        assert box.x1 == 170
        assert box.y1 == 370
        assert box.x2 == 830
        assert box.y2 == 1230


@pytest.mark.asyncio
async def test_detect_tables_with_mistral_error_fallback():
    img = Image.new("RGB", (1000, 1000), color="white")
    with (
        patch("app.features.documents.ingestion.layout_helper.get_settings") as mock_settings,
        patch("app.features.documents.ingestion.layout_helper._call_mistral_ocr_sync", side_effect=RuntimeError("API Network Error")),
    ):
        mock_settings.return_value.ocr_two_stage_enabled = True
        mock_settings.return_value.effective_mistral_api_key = "test-key"
        mock_settings.return_value.mistral_ocr_model = "mistral-ocr-latest"
        mock_settings.return_value.mistral_ocr_timeout_seconds = 10.0

        # Must not raise, gracefully returns empty list
        boxes = await detect_tables_with_mistral(img)
        assert len(boxes) == 0


@pytest.mark.asyncio
async def test_extract_text_from_image_two_stage_crop():
    img = Image.new("RGB", (1000, 1000), color="white")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 900, 800], outline="black", width=5)
    draw.text((200, 200), "جدول شماره ۱", fill="black")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    mock_table_box = TableBoundingBox(x1=100, y1=100, x2=900, y2=800, block_type="table")

    captured_prompts = []

    async def fake_vision_chat(client, model, prompt, mime_type, b64_img, max_tokens):
        captured_prompts.append(prompt)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="| Col1 | Col2 |\n| 1.000 | 2.000 |"))]
        )

    with (
        patch.object(ocr_module, "detect_tables_with_mistral", new=AsyncMock(return_value=[mock_table_box])),
        patch.object(ocr_module, "_probe_rotation", new=AsyncMock(return_value=0)),
        patch.object(ocr_module, "_vision_chat", side_effect=fake_vision_chat),
    ):
        text = await ocr_module.extract_text_from_image(raw_bytes, "png")
        assert "| Col1 | Col2 |" in text
        assert "| 1.000 | 2.000 |" in text
        assert len(captured_prompts) == 1
        assert captured_prompts[0] == ocr_module.SYSTEM_TABLE_OCR_PROMPT


@pytest.mark.asyncio
async def test_extract_text_from_image_fallback_to_full_page():
    img = Image.new("RGB", (1000, 1000), color="white")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 300, 200], fill="black")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    captured_prompts = []

    async def fake_vision_chat(client, model, prompt, mime_type, b64_img, max_tokens):
        captured_prompts.append(prompt)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="متن کامل بدون جدول"))]
        )

    # When no tables or blocks are detected (returns empty list)
    with (
        patch.object(ocr_module, "detect_tables_with_mistral", new=AsyncMock(return_value=[])),
        patch.object(ocr_module, "_probe_rotation", new=AsyncMock(return_value=0)),
        patch.object(ocr_module, "_vision_chat", side_effect=fake_vision_chat),
    ):
        text = await ocr_module.extract_text_from_image(raw_bytes, "png")
        assert text == "متن کامل بدون جدول"
        assert len(captured_prompts) == 1
        assert captured_prompts[0] == ocr_module.SYSTEM_OCR_PROMPT


@pytest.mark.asyncio
async def test_extract_text_from_image_multi_block_cropping():
    img = Image.new("RGB", (1000, 1000), color="white")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 900, 800], fill="black")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    b_header = TableBoundingBox(x1=100, y1=50, x2=900, y2=150, block_type="header")
    b_table = TableBoundingBox(x1=100, y1=200, x2=900, y2=750, block_type="table")
    b_footer = TableBoundingBox(x1=100, y1=800, x2=900, y2=900, block_type="footer")

    mock_layout = DocumentLayoutResult(
        blocks=[b_header, b_table, b_footer],
        table_boxes=[b_table],
    )

    async def fake_vision_chat(client, model, prompt, mime_type, b64_img, max_tokens):
        if prompt == ocr_module.SYSTEM_TABLE_OCR_PROMPT:
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="| Col1 | Col2 |\n| 1.000 | 2.000 |"))]
            )
        # Header or footer prompt
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="متن سربرگ یا پاورقی با کیفیت بالا"))]
        )

    with (
        patch.object(ocr_module, "detect_tables_with_mistral", new=AsyncMock(return_value=mock_layout)),
        patch.object(ocr_module, "_probe_rotation", new=AsyncMock(return_value=0)),
        patch.object(ocr_module, "_vision_chat", side_effect=fake_vision_chat),
    ):
        text = await ocr_module.extract_text_from_image(raw_bytes, "png")
        assert "متن سربرگ یا پاورقی با کیفیت بالا" in text
        assert "| Col1 | Col2 |" in text
        assert "| 1.000 | 2.000 |" in text


def test_replace_markdown_tables():
    full_text = (
        "سربرگ\n\n"
        "| A | B |\n"
        "| 1 | 2 |\n\n"
        "پاورقی"
    )
    precise = "| A | B | C |\n| 1.00 | 2.00 | 3.00 |"
    result = ocr_module.replace_markdown_tables(full_text, [precise])
    assert "سربرگ" in result
    assert "پاورقی" in result
    assert "| 1.00 | 2.00 | 3.00 |" in result
    assert "| 1 | 2 |" not in result


def test_is_redundant_text():
    full = "عنوان پروژه: انتقال آب دریای عمان، پیمانکار: شرکت محور گستر شرق، شماره قرارداد: IMW-CON-03-100"
    snippet_present = "شماره قرارداد: IMW-CON-03-100"
    snippet_absent = "صورتجلسه کمیسیون تحویل موقت قطعه پنجم"

    assert ocr_module._is_redundant_text(snippet_present, full) is True
    assert ocr_module._is_redundant_text(snippet_absent, full) is False

