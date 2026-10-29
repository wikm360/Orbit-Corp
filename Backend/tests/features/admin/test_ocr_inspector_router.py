import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_ocr_inspector_html_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # /api/v1/admin/ocr-inspector returns 200 HTML
        resp1 = await client.get("/api/v1/admin/ocr-inspector")
        assert resp1.status_code == 200
        assert "text/html" in resp1.headers["content-type"]
        assert "Orbit Inspector" in resp1.text

        # /db-admin/ocr-inspector redirects unauthenticated requests to /db-admin/login
        resp2 = await client.get("/db-admin/ocr-inspector", follow_redirects=False)
        assert resp2.status_code in (200, 302)


@pytest.mark.asyncio
async def test_ocr_debug_list_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/ocr-debug/list")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_ocr_debug_nonexistent_doc():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/ocr-debug/nonexistent-id-999")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_documents_inspect_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/ocr-inspector")
        assert resp.status_code == 200
        assert "بازرسی متنی اسناد و صفحات" in resp.text

        list_resp = await client.get("/api/v1/admin/documents-inspect/list")
        assert list_resp.status_code == 200
        assert isinstance(list_resp.json(), list)

        detail_resp = await client.get("/api/v1/admin/documents-inspect/00000000-0000-0000-0000-000000000000")
        assert detail_resp.status_code == 404


@pytest.mark.asyncio
async def test_documents_inspect_detail_existing_document(db_session):
    import uuid
    from app.features.auth.models import User, UserRole
    from app.features.access_control.models import Team
    from app.features.projects.models import Project
    from app.features.documents.models import Document, DocumentStatus, OcrCache

    test_user = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="pw",
        role=UserRole.ADMIN,
    )
    db_session.add(test_user)
    await db_session.flush()

    team = Team(id=uuid.uuid4(), name="Inspect Team", created_by=test_user.id)
    db_session.add(team)
    await db_session.flush()

    project = Project(id=uuid.uuid4(), team_id=team.id, name="Inspect Project", created_by=test_user.id)
    db_session.add(project)
    await db_session.flush()

    doc = Document(
        id=uuid.uuid4(),
        project_id=project.id,
        filename="inspect_test.xlsx",
        file_path="/tmp/fake_inspect_test.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content_hash="mock_hash_inspect_test",
        status=DocumentStatus.READY,
    )
    db_session.add(doc)

    cache_entry = OcrCache(
        cache_key="fake-xlsx-cache-key",
        vision_model="gapgpt",
        text="Sample cell content",
        rotation=0,
        document_id=doc.id,
        source_filename=doc.filename,
        page_number=1,
    )
    db_session.add(cache_entry)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/admin/documents-inspect/{doc.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(doc.id)
        assert data["filename"] == "inspect_test.xlsx"
        assert data["ocr_cache_count"] == 1
        assert data["project_name"] == "Inspect Project"

        # Test purge-ocr-cache endpoint
        purge_resp = await client.post(f"/api/v1/admin/documents-inspect/{doc.id}/purge-ocr-cache")
        assert purge_resp.status_code == 200
        assert purge_resp.json()["deleted_count"] >= 1

        # Check detail again: ocr_cache_count should be 0
        detail_after = await client.get(f"/api/v1/admin/documents-inspect/{doc.id}")
        assert detail_after.status_code == 200
        assert detail_after.json()["ocr_cache_count"] == 0



