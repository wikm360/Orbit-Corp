import io
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image
from pypdf import PdfWriter

from app.core.config import get_settings
from app.features.chat.models import Conversation, ConversationType
from app.features.documents import service as documents_service
from app.features.documents.ingestion.chunker import chunk_document_pages
from app.features.documents.ingestion.ocr import extract_text_from_image, optimize_image_for_ocr
from app.features.documents.ingestion.parser import (
    DocumentPage,
    ExtractedImage,
    parse_document_pages,
)
from app.features.documents.ingestion.pipeline import (
    ChunkStep,
    IngestionContext,
    OCRStep,
    ParseStep,
    PersistStep,
    ReconstructStep,
    run_ingestion_pipeline,
)
from app.features.documents.ingestion.reconstructor import (
    cleanup_reconstructed_files,
    get_reconstructed_json_path,
    get_reconstructed_txt_path,
    load_reconstructed_document,
    save_reconstructed_document,
)
from app.features.documents.models import Document, DocumentChunk, DocumentStatus


def _create_sample_png(tmp_path: Path, width: int = 100, height: int = 100) -> Path:
    img = Image.new("RGB", (width, height), color="white")
    png_path = tmp_path / "sample.png"
    img.save(png_path)
    return png_path


def test_optimize_image_for_ocr(tmp_path):
    large_img = Image.new("RGBA", (3000, 1500), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    large_img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    optimized, mime_type = optimize_image_for_ocr(raw_bytes, max_dimension=1000)
    assert mime_type == "jpeg"
    with Image.open(io.BytesIO(optimized)) as pil_res:
        assert max(pil_res.size) <= 1000
        assert pil_res.mode == "RGB"


@pytest.mark.asyncio
async def test_parse_image_file_as_document(tmp_path):
    png_path = _create_sample_png(tmp_path, width=200, height=150)
    pages = parse_document_pages(str(png_path))
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert len(pages[0].images) == 1
    assert pages[0].images[0].width == 200
    assert pages[0].images[0].height == 150


@pytest.mark.asyncio
async def test_ocr_step_enriches_page_text():
    sample_img = ExtractedImage(
        data=b"fake-image-bytes-at-least-100-bytes-length-to-pass-minimum-check-123456789012345678901234567890",
        name="chart.png",
        format="png",
        width=200,
        height=200,
    )
    page = DocumentPage(
        page_number=5,
        text="متن اصلی صفحه پنجم",
        images=[sample_img],
    )

    context = IngestionContext(
        document_id=uuid.uuid4(),
        file_path="/fake/path.pdf",
        db=None,
        pages=[page],
    )

    with patch(
        "app.features.documents.ingestion.pipeline.extract_text_from_image",
        new=AsyncMock(return_value="جدول فروش پاییز: ۱۰۰ میلیون تومان"),
    ):
        await OCRStep().run(context)

    assert "متن اصلی صفحه پنجم" in page.text
    assert "جدول فروش پاییز: ۱۰۰ میلیون تومان" in page.text
    assert "[محتوای استخراج‌شده از تصویر / جدول]:" in page.text


def test_save_and_load_reconstructed_document(tmp_path):
    file_path = str(tmp_path / "doc.pdf")
    pages = [
        DocumentPage(page_number=1, text="صفحه اول"),
        DocumentPage(page_number=2, text="صفحه دوم همراه با تصویر OCR شده"),
    ]

    full_txt, json_payload = save_reconstructed_document(file_path, "doc.pdf", pages)
    assert "--- [صفحه 1] ---" in full_txt
    assert "--- [صفحه 2] ---" in full_txt
    assert json_payload["total_pages"] == 2

    loaded = load_reconstructed_document(file_path)
    assert loaded is not None
    assert loaded["filename"] == "doc.pdf"
    assert loaded["total_pages"] == 2
    assert loaded["pages"][1]["text"] == "صفحه دوم همراه با تصویر OCR شده"

    cleanup_reconstructed_files(file_path)
    assert not get_reconstructed_txt_path(file_path).exists()
    assert not get_reconstructed_json_path(file_path).exists()


def test_chunk_document_pages_preserves_page_numbers():
    pages = [
        DocumentPage(page_number=1, text="پاراگراف کوتاه صفحه اول"),
        DocumentPage(page_number=2, text="پاراگراف کوتاه صفحه دوم"),
        DocumentPage(page_number=3, text="پاراگراف طولانی صفحه سوم " * 100),
    ]

    chunks = chunk_document_pages(pages, chunk_size_tokens=100, overlap_tokens=20)
    assert len(chunks) >= 3

    pages_found = set()
    for chunk in chunks:
        assert "page" in chunk.metadata
        assert chunk.metadata["total_pages"] == 3
        pages_found.add(chunk.metadata["page"])

    assert pages_found == {1, 2, 3}


@pytest.mark.asyncio
async def test_get_document_page_range_with_real_pages(client, db_session, tmp_path):
    file_path = str(tmp_path / "handbook.pdf")
    pages = [
        DocumentPage(page_number=1, text="متن صفحه اول"),
        DocumentPage(page_number=2, text="متن صفحه دوم اختصاصی"),
        DocumentPage(page_number=3, text="متن صفحه سوم"),
    ]
    save_reconstructed_document(file_path, "handbook.pdf", pages)

    from tests.features.documents.test_document_reads import _leader_with_project, _seed_conversation

    leader_id, project_id = await _leader_with_project(client, "realpages")
    conversation = await _seed_conversation(db_session, project_id=uuid.UUID(project_id))

    document = Document(
        filename="handbook.pdf",
        file_path=file_path,
        content_type="application/pdf",
        status=DocumentStatus.READY,
        content_hash=str(uuid.uuid4()),
        embedding_model=get_settings().embedding_model,
        project_id=uuid.UUID(project_id),
    )
    db_session.add(document)
    await db_session.flush()

    for p in pages:
        db_session.add(
            DocumentChunk(
                document_id=document.id,
                content=p.text,
                chunk_index=p.page_number - 1,
                embedding=[0.0] * get_settings().embedding_dimensions,
                chunk_metadata={"page": p.page_number, "total_pages": 3},
            )
        )
    await db_session.commit()

    outline = await documents_service.get_document_outline(
        db_session,
        document.id,
        project_id=uuid.UUID(project_id),
        conversation_id=conversation.id,
    )
    assert outline["total_pages"] == 3

    page_text = await documents_service.get_document_page_range(
        db_session,
        document.id,
        start_page=2,
        end_page=2,
        project_id=uuid.UUID(project_id),
        conversation_id=conversation.id,
    )
    assert "متن صفحه دوم اختصاصی" in page_text
    assert "متن صفحه اول" not in page_text
    assert "متن صفحه سوم" not in page_text


@pytest.mark.asyncio
async def test_pipeline_e2e_with_ocr_and_pages(client, db_session, tmp_path):
    from sqlalchemy import select
    from tests.features.documents.test_document_reads import _leader_with_project

    leader_id, project_id = await _leader_with_project(client, "e2eocr")

    doc_path = tmp_path / "report.txt"
    doc_path.write_text("گزارش سالیانه مالی\nبخش اول سود و زیان", encoding="utf-8")

    document = Document(
        filename="report.txt",
        file_path=str(doc_path),
        content_type="text/plain",
        status=DocumentStatus.PROCESSING,
        content_hash=str(uuid.uuid4()),
        project_id=uuid.UUID(project_id),
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    class MockEmbeddingProvider:
        async def embed(self, texts):
            dim = get_settings().embedding_dimensions
            return [[0.1] * dim for _ in texts]

    with patch(
        "app.features.documents.ingestion.pipeline.get_embedding_provider",
        return_value=MockEmbeddingProvider(),
    ):
        await run_ingestion_pipeline(document.id, str(doc_path))

    await db_session.refresh(document)
    assert document.status == DocumentStatus.READY

    assert get_reconstructed_txt_path(str(doc_path)).exists()
    assert get_reconstructed_json_path(str(doc_path)).exists()

    result = await db_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document.id)
    )
    chunks = list(result.scalars().all())
    assert len(chunks) > 0
    assert chunks[0].chunk_metadata.get("page") == 1
