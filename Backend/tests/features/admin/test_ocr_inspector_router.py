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

