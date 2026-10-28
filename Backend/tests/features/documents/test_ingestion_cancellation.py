"""Cancelling / deleting a document while the worker is processing it must stop the pipeline without a FAILED status,
without a READY overwrite and without leftover chunks."""
import uuid

import pytest
from sqlalchemy import func, select, update

from app.core.config import Settings
from app.core.database import async_session_factory
from app.features.auth.models import User
from app.features.documents.cancellation import IngestionCancelled
from app.features.documents.ingestion import pipeline
from app.features.documents.models import Document, DocumentChunk, DocumentStatus
from app.features.projects.models import Project
from app.features.access_control.models import Team


class _StubEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * Settings().embedding_dimensions for _ in texts]


async def _seed_document(db_session, tmp_path) -> Document:
    user = User(email=f"{uuid.uuid4()}@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    team = Team(name=f"t-{uuid.uuid4()}")
    db_session.add(team)
    await db_session.flush()
    project = Project(name="p", team_id=team.id, created_by=user.id)
    db_session.add(project)
    await db_session.flush()
    path = tmp_path / "note.txt"
    path.write_text("Our refund policy: five business days.")
    document = Document(
        filename="note.txt",
        file_path=str(path),
        content_type="text/plain",
        status=DocumentStatus.PROCESSING,
        content_hash=str(uuid.uuid4()),
        project_id=project.id,
        uploaded_by=user.id,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


async def _set_status(document_id: uuid.UUID, status: DocumentStatus) -> None:
    async with async_session_factory() as session:
        await session.execute(update(Document).where(Document.id == document_id).values(status=status))
        await session.commit()


async def _state(document_id: uuid.UUID) -> tuple[DocumentStatus | None, int]:
    async with async_session_factory() as session:
        status = (await session.execute(select(Document.status).where(Document.id == document_id))).scalar_one_or_none()
        chunks = await session.scalar(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        return status, chunks


@pytest.fixture(autouse=True)
def _stubs(monkeypatch):
    monkeypatch.setattr(pipeline, "get_embedding_provider", lambda: _StubEmbeddingProvider())

    async def no_publish(*_a, **_kw):
        return None

    monkeypatch.setattr(pipeline, "publish_event", no_publish)


async def test_a_document_cancelled_while_queued_is_not_processed(db_session, tmp_path, monkeypatch):
    document = await _seed_document(db_session, tmp_path)
    await _set_status(document.id, DocumentStatus.CANCELLED)

    def explode(_path):
        raise AssertionError("a cancelled document must not even be parsed")

    monkeypatch.setattr(pipeline, "parse_document_pages", explode)
    await pipeline.run_ingestion_pipeline(document.id, document.file_path)

    assert await _state(document.id) == (DocumentStatus.CANCELLED, 0)


async def test_a_document_deleted_while_queued_is_not_processed(db_session, tmp_path, monkeypatch):
    document = await _seed_document(db_session, tmp_path)
    document_id, file_path = document.id, document.file_path
    await db_session.delete(document)
    await db_session.commit()

    def explode(_path):
        raise AssertionError("a deleted document must not even be parsed")

    monkeypatch.setattr(pipeline, "parse_document_pages", explode)
    await pipeline.run_ingestion_pipeline(document_id, file_path)  # no exception, no work

    assert await _state(document_id) == (None, 0)


async def test_cancel_between_steps_stops_the_pipeline_and_keeps_the_cancelled_status(db_session, tmp_path, monkeypatch):
    document = await _seed_document(db_session, tmp_path)
    ran: list[str] = []

    class Step(pipeline.IngestionStep):
        def __init__(self, name, cancel=False):
            self.name, self.cancel = name, cancel

        async def run(self, context):
            ran.append(self.name)
            if self.cancel:
                await _set_status(context.document_id, DocumentStatus.CANCELLED)

    monkeypatch.setattr(pipeline, "DEFAULT_PIPELINE", [Step("parse"), Step("ocr", cancel=True), Step("persist")])
    await pipeline.run_ingestion_pipeline(document.id, document.file_path)  # does not raise

    assert ran == ["parse", "ocr"]  # nothing after the step during which the cancel landed
    assert await _state(document.id) == (DocumentStatus.CANCELLED, 0)


async def test_a_cancel_landing_after_the_last_check_is_not_overwritten_by_ready_and_drops_the_chunks(
    db_session, tmp_path, monkeypatch
):
    document = await _seed_document(db_session, tmp_path)

    class PersistThenCancel(pipeline.IngestionStep):
        async def run(self, context):
            context.db.add(
                DocumentChunk(
                    document_id=context.document_id,
                    content="x",
                    chunk_index=0,
                    embedding=[0.0] * Settings().embedding_dimensions,
                )
            )
            await context.db.commit()
            await _set_status(context.document_id, DocumentStatus.CANCELLED)

    async def never_stops(*_a, **_kw):
        return None

    monkeypatch.setattr(pipeline, "DEFAULT_PIPELINE", [PersistThenCancel()])
    monkeypatch.setattr(pipeline, "_assert_still_processing", never_stops)
    await pipeline.run_ingestion_pipeline(document.id, document.file_path)

    assert await _state(document.id) == (DocumentStatus.CANCELLED, 0)


async def test_a_document_deleted_mid_run_ends_quietly(db_session, tmp_path, monkeypatch):
    document = await _seed_document(db_session, tmp_path)

    class DeleteIt(pipeline.IngestionStep):
        async def run(self, context):
            async with async_session_factory() as session:
                await session.delete(await session.get(Document, context.document_id))
                await session.commit()

    monkeypatch.setattr(pipeline, "DEFAULT_PIPELINE", [DeleteIt(), DeleteIt()])
    await pipeline.run_ingestion_pipeline(document.id, document.file_path)  # no exception
    assert await _state(document.id) == (None, 0)


async def test_an_error_in_a_cancelled_document_does_not_turn_it_into_failed(db_session, tmp_path, monkeypatch):
    document = await _seed_document(db_session, tmp_path)

    class CancelThenBreak(pipeline.IngestionStep):
        async def run(self, context):
            await _set_status(context.document_id, DocumentStatus.CANCELLED)
            raise RuntimeError("boom after cancel")

    monkeypatch.setattr(pipeline, "DEFAULT_PIPELINE", [CancelThenBreak()])
    with pytest.raises(RuntimeError):
        await pipeline.run_ingestion_pipeline(document.id, document.file_path)
    assert (await _state(document.id))[0] == DocumentStatus.CANCELLED


async def test_a_real_error_still_marks_the_document_failed(db_session, tmp_path, monkeypatch):
    document = await _seed_document(db_session, tmp_path)

    class Break(pipeline.IngestionStep):
        async def run(self, context):
            raise RuntimeError("parser exploded")

    monkeypatch.setattr(pipeline, "DEFAULT_PIPELINE", [Break()])
    with pytest.raises(RuntimeError):
        await pipeline.run_ingestion_pipeline(document.id, document.file_path)
    assert (await _state(document.id))[0] == DocumentStatus.FAILED


async def test_a_normal_run_still_finishes_ready(db_session, tmp_path):
    document = await _seed_document(db_session, tmp_path)
    await pipeline.run_ingestion_pipeline(document.id, document.file_path)
    status, chunks = await _state(document.id)
    assert status == DocumentStatus.READY and chunks >= 1


async def test_cancel_flag_stops_paid_ocr_calls(monkeypatch):
    calls: list[int] = []

    async def fake_vision(*_a, **_kw):
        calls.append(1)
        return "text"

    async def flagged(_document_id):
        return True

    monkeypatch.setattr(pipeline, "extract_text_from_image", fake_vision)
    monkeypatch.setattr(pipeline, "is_cancel_requested", flagged)
    reader = pipeline._OcrReader(None, 2)
    with pytest.raises(IngestionCancelled):
        await reader.read(b"image-bytes", "png", debug_info={"document_id": str(uuid.uuid4()), "page_number": 1})
    assert calls == []
