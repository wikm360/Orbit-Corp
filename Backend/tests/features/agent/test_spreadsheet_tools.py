import uuid

import pytest
from openpyxl import Workbook

from app.core.dependencies import UserContext
from app.core.exceptions import BadRequestError
from app.features.access_control.models import Team
from app.features.agent.tools.registry import build_default_registry
from app.features.agent.tools.spreadsheet_tools import DescribeSpreadsheetTool, QuerySpreadsheetTool
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType
from app.features.documents.models import Document, DocumentStatus
from app.features.projects.models import Project


async def _setup(db_session, tmp_path, *, filename="بیمه.xlsx", in_project=True, content_type="application/vnd.ms-excel"):
    path = tmp_path / "ins.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["نام", "مبلغ"])
    ws.append(["علیرضا پاریاب", 15979160])
    ws.append(["مصطفی محمودی", 16721096])
    wb.save(path)

    team = Team(id=uuid.uuid4(), name="تیم")
    project = Project(id=uuid.uuid4(), team_id=team.id, name="پروژه")
    db_session.add_all([team, project])
    await db_session.flush()
    user = User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@example.com", hashed_password="x", role="user")
    db_session.add(user)
    await db_session.flush()
    conv = Conversation(id=uuid.uuid4(), type=ConversationType.PERSONAL, created_by=user.id, linked_project_id=project.id)
    db_session.add(conv)
    await db_session.flush()
    doc = Document(
        id=uuid.uuid4(),
        filename=filename,
        file_path=str(path),
        content_type=content_type,
        status=DocumentStatus.READY,
        content_hash="h" + uuid.uuid4().hex,
        project_id=project.id if in_project else None,
        conversation_id=None if in_project else conv.id,
    )
    db_session.add(doc)
    await db_session.commit()
    return doc, UserContext(user=user, project_ids=[project.id]), conv


@pytest.mark.asyncio
async def test_describe_then_query_by_filename(db_session, tmp_path):
    doc, context, conv = await _setup(db_session, tmp_path)
    described = await DescribeSpreadsheetTool().execute(db=db_session, context=context, conversation=conv, document_id="@بیمه.xlsx")
    assert "Sheet1" in described.text and "مبلغ" in described.text

    result = await QuerySpreadsheetTool().execute(
        db=db_session,
        context=context,
        conversation=conv,
        document_id=str(doc.id),
        sql="SELECT _row, مبلغ FROM Sheet1 WHERE نام LIKE '%پاریاب%'",
    )
    assert "15979160" in result.text and "16721096" not in result.text
    assert "File columns" in result.text
    assert result.citations[0].document_id == str(doc.id)


@pytest.mark.asyncio
async def test_query_rejects_write_and_non_spreadsheet(db_session, tmp_path):
    doc, context, conv = await _setup(db_session, tmp_path)
    with pytest.raises(BadRequestError):
        await QuerySpreadsheetTool().execute(
            db=db_session, context=context, conversation=conv, document_id=str(doc.id), sql="DROP TABLE Sheet1"
        )

    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    doc.file_path = str(pdf)
    await db_session.commit()
    with pytest.raises(BadRequestError, match="not a spreadsheet"):
        await DescribeSpreadsheetTool().execute(db=db_session, context=context, conversation=conv, document_id=str(doc.id))


@pytest.mark.asyncio
async def test_other_users_project_document_is_not_reachable(db_session, tmp_path):
    doc, context, conv = await _setup(db_session, tmp_path)
    outsider = UserContext(user=context.user, project_ids=[])  # same conversation but no project scope
    other_conv = Conversation(id=uuid.uuid4(), type=ConversationType.PERSONAL, created_by=context.id)
    db_session.add(other_conv)
    await db_session.commit()
    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await QuerySpreadsheetTool().execute(
            db=db_session, context=outsider, conversation=other_conv, document_id=str(doc.id), sql="SELECT 1"
        )


@pytest.mark.asyncio
async def test_tools_are_registered(db_session):
    names = [t.name for t in build_default_registry()._tools.values()]
    assert "describe_spreadsheet" in names and "query_spreadsheet" in names
