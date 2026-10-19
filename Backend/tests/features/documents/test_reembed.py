import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.features.access_control.models import Team
from app.features.documents.models import Document, DocumentChunk, DocumentStatus
from app.features.documents.reembed import reembed_documents, reembed_memories
from app.features.memory.models import MemoryCategory, ProjectMemory
from app.features.projects.models import Project

DIM = get_settings().embedding_dimensions


class _ConstantProvider:
    """Every text gets the same unit vector, so a re-embedded row is easy to recognise."""

    async def embed(self, texts):
        vector = [0.0] * DIM
        vector[3] = 1.0
        return [list(vector) for _ in texts]


async def _project(db):
    team = Team(name=f"T-{uuid.uuid4()}")
    db.add(team)
    await db.flush()
    project = Project(team_id=team.id, name="P")
    db.add(project)
    await db.flush()
    return project


async def _document(db, project, model):
    document = Document(
        filename="a.txt", file_path="/dev/null", content_type="text/plain", status=DocumentStatus.READY,
        content_hash=str(uuid.uuid4()), embedding_model=model, project_id=project.id,
    )
    db.add(document)
    await db.flush()
    for index in range(3):
        old = [0.0] * DIM
        old[0] = 1.0
        db.add(DocumentChunk(document_id=document.id, content=f"chunk {index}", chunk_index=index, embedding=old))
    await db.commit()
    return document


async def test_only_documents_embedded_with_another_model_are_reembedded(db_session):
    project = await _project(db_session)
    stale_id = (await _document(db_session, project, "old-model")).id
    current_id = (await _document(db_session, project, get_settings().embedding_model)).id

    stats = await reembed_documents(db_session, _ConstantProvider())

    assert stats == {"documents": 1, "chunks": 3}
    db_session.expire_all()
    stale_vectors = (await db_session.execute(select(DocumentChunk.embedding).where(DocumentChunk.document_id == stale_id))).scalars().all()
    current_vectors = (await db_session.execute(select(DocumentChunk.embedding).where(DocumentChunk.document_id == current_id))).scalars().all()
    assert all(v[3] == 1.0 for v in stale_vectors)
    assert all(v[0] == 1.0 for v in current_vectors)
    refreshed = await db_session.get(Document, stale_id)
    assert refreshed.embedding_model == get_settings().embedding_model


async def test_dry_run_changes_nothing(db_session):
    project = await _project(db_session)
    stale = await _document(db_session, project, "old-model")

    stats = await reembed_documents(db_session, _ConstantProvider(), dry_run=True)

    assert stats == {"documents": 1, "chunks": 3}
    refreshed = await db_session.get(Document, stale.id)
    assert refreshed.embedding_model == "old-model"


async def test_memories_are_reembedded(db_session):
    project = await _project(db_session)
    old = [0.0] * DIM
    old[0] = 1.0
    db_session.add(ProjectMemory(project_id=project.id, fact_text="fact", category=MemoryCategory.CONVENTION, embedding=old))
    await db_session.commit()

    assert await reembed_memories(db_session, _ConstantProvider()) == {"memories": 1}

    db_session.expire_all()
    memory = (await db_session.execute(select(ProjectMemory))).scalar_one()
    assert memory.embedding[3] == 1.0
