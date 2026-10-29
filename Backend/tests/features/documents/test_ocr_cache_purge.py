import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.features.documents.ingestion.ocr_cache import (
    ocr_cache_key,
    put_cached_ocr,
    get_cached_ocr,
    purge_document_ocr_cache,
    purge_all_ocr_cache,
)
from app.features.documents.models import Document, DocumentStatus, OcrCache
from app.features.documents.service import delete_document
from sqlalchemy import select


@pytest.mark.asyncio
async def test_ocr_cache_stores_document_metadata_and_purges_cleanly(db_session):
    doc_id = uuid.uuid4()
    key1 = "test-key-1:reader"
    key2 = "test-key-2:reader"

    # Put cached entries with document metadata
    await put_cached_ocr(
        db_session,
        key=key1,
        text="متن تستی صفحه ۱",
        rotation=0,
        document_id=doc_id,
        source_filename="test_spec.pdf",
        page_number=1,
    )
    await put_cached_ocr(
        db_session,
        key=key2,
        text="متن تستی صفحه ۲",
        rotation=0,
        document_id=doc_id,
        source_filename="test_spec.pdf",
        page_number=2,
    )

    # Verify they exist
    entry1 = await get_cached_ocr(db_session, key1)
    assert entry1 is not None
    assert entry1[0] == "متن تستی صفحه ۱"

    # Purge OCR cache for this document
    purged_count = await purge_document_ocr_cache(db_session, doc_id)
    assert purged_count == 2

    # Verify they are gone
    assert await get_cached_ocr(db_session, key1) is None
    assert await get_cached_ocr(db_session, key2) is None


@pytest.mark.asyncio
async def test_delete_document_automatically_purges_ocr_cache(db_session, tmp_path):
    from app.features.access_control.models import Team
    from app.features.projects.models import Project

    team = Team(id=uuid.uuid4(), name="Test Team")
    db_session.add(team)
    await db_session.flush()

    project = Project(id=uuid.uuid4(), name="Test Project", team_id=team.id)
    db_session.add(project)
    await db_session.flush()

    # Create a physical file
    fake_file = tmp_path / "sample.pdf"
    fake_file.write_bytes(b"%PDF-fake")

    doc = Document(
        id=uuid.uuid4(),
        filename="sample.pdf",
        file_path=str(fake_file),
        content_type="application/pdf",
        content_hash="dummyhash",
        status=DocumentStatus.READY,
        project_id=project.id,
    )
    db_session.add(doc)
    await db_session.commit()

    key = "sample-cache-key:reader"
    await put_cached_ocr(
        db_session,
        key=key,
        text="متن نمونه در کش",
        document_id=doc.id,
        source_filename=doc.filename,
        page_number=1,
    )

    # Verify cache entry is in DB
    cached = await get_cached_ocr(db_session, key)
    assert cached is not None

    # Delete the document via service
    await delete_document(db_session, doc.id)

    # Verify the OCR cache entry was automatically purged
    assert await get_cached_ocr(db_session, key) is None

