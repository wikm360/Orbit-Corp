import base64
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from app.core.exceptions import BadRequestError, NotFoundError
from app.features.agent.tools import document_tools
from app.features.agent.tools.document_tools import ViewDocumentPageTool
from app.features.agent.tools.registry import build_default_registry
from app.features.documents import service as documents_service
from app.features.documents.ingestion.parser import ExtractedImage
from app.features.documents.models import Document, DocumentStatus
from tests.features.documents.test_document_reads import _leader_with_project, _seed_conversation


async def _seed_file_document(db_session, *, project_id, path: str, filename: str, content_type: str) -> Document:
    document = Document(
        filename=filename,
        file_path=path,
        content_type=content_type,
        status=DocumentStatus.READY,
        content_hash=str(uuid.uuid4()),
        embedding_model="x",
        project_id=project_id,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


def _tool_call_context(conversation):
    # resolve_retrieval_scope: a project group chat is scoped to its own project
    return SimpleNamespace(), conversation


async def test_page_image_of_a_pdf_is_rendered_from_the_original_file(client, db_session, tmp_path):
    _, project_id = await _leader_with_project(client, "pageimg")
    pdf = tmp_path / "plans.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    document = await _seed_file_document(
        db_session, project_id=uuid.UUID(project_id), path=str(pdf), filename="plans.pdf", content_type="application/pdf"
    )
    conversation = await _seed_conversation(db_session, project_id=uuid.UUID(project_id))
    rendered = ExtractedImage(data=b"PNGDATA", name="p.png")

    with patch.object(documents_service, "render_pdf_page", return_value=rendered) as render:
        doc, image, rotation = await documents_service.get_document_page_image(
            db_session, document.id, 75, project_id=uuid.UUID(project_id), conversation_id=conversation.id
        )
    assert doc.id == document.id and image == b"PNGDATA" and rotation is None  # no stored rotation for this document
    render.assert_called_once_with(str(pdf), 75)

    with patch.object(documents_service, "render_pdf_page", return_value=None):
        with pytest.raises(BadRequestError):
            await documents_service.get_document_page_image(
                db_session, document.id, 999, project_id=uuid.UUID(project_id), conversation_id=conversation.id
            )
    with pytest.raises(BadRequestError):  # page numbers start at 1
        await documents_service.get_document_page_image(
            db_session, document.id, 0, project_id=uuid.UUID(project_id), conversation_id=conversation.id
        )


async def test_page_image_for_image_files_and_unsupported_formats(client, db_session, tmp_path):
    _, project_id = await _leader_with_project(client, "pageimg2")
    png = tmp_path / "scan.png"
    Image.new("RGB", (50, 50), "white").save(png)
    docx = tmp_path / "notes.docx"
    docx.write_bytes(b"docx")
    image_doc = await _seed_file_document(
        db_session, project_id=uuid.UUID(project_id), path=str(png), filename="scan.png", content_type="image/png"
    )
    docx_doc = await _seed_file_document(
        db_session, project_id=uuid.UUID(project_id), path=str(docx), filename="notes.docx", content_type="application/x"
    )
    conversation = await _seed_conversation(db_session, project_id=uuid.UUID(project_id))
    scope = dict(project_id=uuid.UUID(project_id), conversation_id=conversation.id)

    _, data, _ = await documents_service.get_document_page_image(db_session, image_doc.id, 1, **scope)
    assert data == png.read_bytes()
    with pytest.raises(BadRequestError):
        await documents_service.get_document_page_image(db_session, image_doc.id, 2, **scope)
    with pytest.raises(BadRequestError, match="PDF and image"):
        await documents_service.get_document_page_image(db_session, docx_doc.id, 1, **scope)


async def test_page_image_is_limited_to_what_the_conversation_can_see(client, db_session, tmp_path):
    admin_token = (await client.post("/api/v1/auth/register", json={"email": "admin-scope@example.com", "password": "supersecret"})).json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    _, project_a = await _leader_with_project(client, "scopea", headers)
    _, project_b = await _leader_with_project(client, "scopeb", headers)
    pdf = tmp_path / "secret.pdf"
    pdf.write_bytes(b"%PDF")
    document = await _seed_file_document(
        db_session, project_id=uuid.UUID(project_b), path=str(pdf), filename="secret.pdf", content_type="application/pdf"
    )
    conversation_a = await _seed_conversation(db_session, project_id=uuid.UUID(project_a))

    with patch.object(documents_service, "render_pdf_page", return_value=ExtractedImage(data=b"x")) as render:
        with pytest.raises(NotFoundError):
            await documents_service.get_document_page_image(
                db_session, document.id, 1, project_id=uuid.UUID(project_a), conversation_id=conversation_a.id
            )
    render.assert_not_called()  # nothing is rendered for a document outside the scope


async def test_tool_attaches_the_prepared_page_image_and_cites_the_page():
    document = SimpleNamespace(id=uuid.uuid4(), filename="plans.pdf")
    conversation = SimpleNamespace(id=uuid.uuid4())
    with (
        patch.object(document_tools, "resolve_retrieval_scope", return_value=None),
        patch.object(documents_service, "get_document_page_image", new=AsyncMock(return_value=(document, b"raw", None))),
        patch.object(document_tools, "prepare_image_for_ocr", new=AsyncMock(return_value=(b"JPEGDATA", "jpeg"))) as prepare,
    ):
        result = await ViewDocumentPageTool().execute(
            db=None, context=SimpleNamespace(), conversation=conversation, document_id=str(document.id), page_number=75
        )
    prepare.assert_awaited_once_with(b"raw", rotation=None)  # same orientation / blank / size clean-up as OCR
    assert result.images == ["data:image/jpeg;base64," + base64.b64encode(b"JPEGDATA").decode()]
    assert "plans.pdf (صفحه 75)" in result.text and "attached in the next message" in result.text
    [citation] = result.citations
    assert citation.page == 75 and citation.chunk_index == -1 and citation.document_id == str(document.id)


async def test_tool_reports_blank_pages_and_preparation_failures_as_text():
    document = SimpleNamespace(id=uuid.uuid4(), filename="plans.pdf")
    kwargs = dict(db=None, context=SimpleNamespace(), conversation=SimpleNamespace(id=uuid.uuid4()),
                  document_id=str(document.id), page_number=3)
    with (
        patch.object(document_tools, "resolve_retrieval_scope", return_value=None),
        patch.object(documents_service, "get_document_page_image", new=AsyncMock(return_value=(document, b"raw", None))),
    ):
        with patch.object(document_tools, "prepare_image_for_ocr", new=AsyncMock(return_value=None)):
            blank = await ViewDocumentPageTool().execute(**kwargs)
        assert "blank" in blank.text and blank.images == [] and blank.citations == []
        with patch.object(document_tools, "prepare_image_for_ocr", new=AsyncMock(side_effect=RuntimeError("bad image"))):
            failed = await ViewDocumentPageTool().execute(**kwargs)
        assert "could not be prepared" in failed.text and failed.images == []


def test_tool_is_registered_unless_switched_off(monkeypatch):
    names = lambda: [t["function"]["name"] for t in build_default_registry().to_openai_tools()]  # noqa: E731
    assert "view_document_page" in names()
    monkeypatch.setattr(document_tools.get_settings(), "agent_page_vision_enabled", False)
    assert "view_document_page" not in names()


async def test_the_rotation_stored_at_ingestion_is_passed_on_so_the_chat_turn_does_not_detect_it_again():
    from app.features.documents.ingestion import ocr as ocr_module

    document = SimpleNamespace(id=uuid.uuid4(), filename="plans.pdf")
    with (
        patch.object(document_tools, "resolve_retrieval_scope", return_value=None),
        patch.object(documents_service, "get_document_page_image", new=AsyncMock(return_value=(document, b"raw", 270))),
        patch.object(document_tools, "prepare_image_for_ocr", new=AsyncMock(return_value=(b"J", "jpeg"))) as prepare,
    ):
        await ViewDocumentPageTool().execute(
            db=None, context=SimpleNamespace(), conversation=SimpleNamespace(id=uuid.uuid4()), document_id=str(document.id), page_number=75
        )
    prepare.assert_awaited_once_with(b"raw", rotation=270)
    assert ocr_module.prepare_image_for_ocr  # the real function takes the same keyword


async def test_the_stored_rotation_is_read_from_the_reconstructed_page_metadata(client, db_session, tmp_path):
    from app.features.documents.ingestion.reconstructor import save_reconstructed_document
    from app.features.documents.ingestion.parser import DocumentPage

    _, project_id = await _leader_with_project(client, "rotmeta")
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF")
    document = await _seed_file_document(
        db_session, project_id=uuid.UUID(project_id), path=str(pdf), filename="scan.pdf", content_type="application/pdf"
    )
    save_reconstructed_document(str(pdf), "scan.pdf", [
        DocumentPage(page_number=1, text="a", metadata={"page": 1}),
        DocumentPage(page_number=2, text="b", metadata={"page": 2, "rotation": 270}),
        DocumentPage(page_number=3, text="c", metadata={"page": 3, "rotation": 0}),
    ])
    conversation = await _seed_conversation(db_session, project_id=uuid.UUID(project_id))
    scope = dict(project_id=uuid.UUID(project_id), conversation_id=conversation.id)
    with patch.object(documents_service, "render_pdf_page", return_value=ExtractedImage(data=b"x")):
        rotations = [
            (await documents_service.get_document_page_image(db_session, document.id, page, **scope))[2] for page in (1, 2, 3)
        ]
    assert rotations == [None, 270, 0]  # unknown, known sideways, known upright (0 is a real answer, not "missing")


async def test_read_entire_document_returns_citations_and_content():
    from app.features.agent.tools.document_tools import ReadEntireDocumentTool

    doc_id = uuid.uuid4()
    mock_doc = SimpleNamespace(id=doc_id, filename="letter.png")

    with (
        patch.object(document_tools, "resolve_retrieval_scope", return_value=None),
        patch.object(documents_service, "get_accessible_document", new=AsyncMock(return_value=mock_doc)),
        patch.object(documents_service, "get_full_document_content", new=AsyncMock(return_value="متن کامل نامه اداری OCR شده")),
    ):
        result = await ReadEntireDocumentTool().execute(
            db=None,
            context=SimpleNamespace(),
            conversation=SimpleNamespace(id=uuid.uuid4()),
            document_id=str(doc_id),
        )

    assert result.text == "متن کامل نامه اداری OCR شده"
    assert len(result.citations) == 1
    assert result.citations[0].document_filename == "letter.png"
    assert result.citations[0].snippet == "متن کامل نامه اداری OCR شده"
    assert result.citations[0].score == 1.0


async def test_read_document_pages_returns_citations_and_content():
    from app.features.agent.tools.document_tools import ReadDocumentPagesTool

    doc_id = uuid.uuid4()
    mock_doc = SimpleNamespace(id=doc_id, filename="contract.pdf")

    with (
        patch.object(document_tools, "resolve_retrieval_scope", return_value=None),
        patch.object(documents_service, "get_accessible_document", new=AsyncMock(return_value=mock_doc)),
        patch.object(documents_service, "get_document_page_range", new=AsyncMock(return_value="صفحه ۱ قرارداد")),
    ):
        result = await ReadDocumentPagesTool().execute(
            db=None,
            context=SimpleNamespace(),
            conversation=SimpleNamespace(id=uuid.uuid4()),
            document_id=str(doc_id),
            start_page=1,
            end_page=1,
        )

    assert result.text == "صفحه ۱ قرارداد"
    assert len(result.citations) == 1
    assert result.citations[0].document_filename == "contract.pdf"
    assert result.citations[0].page == 1
