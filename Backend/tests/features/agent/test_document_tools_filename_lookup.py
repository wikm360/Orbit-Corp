import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.dependencies import UserContext
from app.features.agent.tools.document_tools import (
    GetDocumentInfoTool,
    ReadDocumentPagesTool,
    ReadEntireDocumentTool,
)
from app.features.access_control.models import Team
from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType
from app.features.documents.models import Document, DocumentStatus
from app.features.projects.models import Project


@pytest.mark.asyncio
async def test_tools_resolve_document_by_filename(db_session):
    team_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    project_id = uuid.uuid4()

    team = Team(id=team_id, name="تیم مهندسی")
    db_session.add(team)
    project = Project(id=project_id, team_id=team_id, name="پروژه اول")
    db_session.add(project)
    await db_session.flush()

    doc = Document(
        id=doc_id,
        filename="ضابطه773.pdf",
        file_path="/fake/ضابطه773.pdf",
        content_type="application/pdf",
        status=DocumentStatus.READY,
        content_hash="fakehash",
        project_id=project_id,
        conversation_id=None,
    )
    db_session.add(doc)
    await db_session.commit()

    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hash",
        role="user",
    )
    db_session.add(user)
    await db_session.flush()

    context = UserContext(
        user=user,
        project_ids=[project_id],
    )
    conv = Conversation(
        id=conv_id,
        type=ConversationType.PERSONAL,
        created_by=context.id,
        linked_project_id=project_id,
    )

    info_tool = GetDocumentInfoTool()
    with patch(
        "app.features.documents.service.get_document_info",
        new=AsyncMock(return_value={"total_pages": 189, "filename": "ضابطه773.pdf"}),
    ):
        # 1. By filename with @ prefix
        res1 = await info_tool.execute(
            db=db_session, context=context, conversation=conv, filename="@ضابطه773.pdf"
        )
        assert '"total_pages": 189' in res1.text

        # 2. Passed into document_id argument as filename string
        res2 = await info_tool.execute(
            db=db_session, context=context, conversation=conv, document_id="ضابطه773.pdf"
        )
        assert '"total_pages": 189' in res2.text

    read_pages_tool = ReadDocumentPagesTool()
    with patch(
        "app.features.documents.service.get_document_page_range",
        new=AsyncMock(return_value="متن استخراج‌شده صفحه ۱ تا ۵"),
    ):
        res3 = await read_pages_tool.execute(
            db=db_session,
            context=context,
            conversation=conv,
            document_id="@ضابطه773.pdf",
            start_page=1,
            end_page=5,
        )
        assert "متن استخراج‌شده صفحه ۱ تا ۵" in res3.text
        assert res3.citations[0].document_filename == "ضابطه773.pdf"

    read_entire_tool = ReadEntireDocumentTool()
    with patch(
        "app.features.documents.service.get_full_document_content",
        new=AsyncMock(return_value="کل متن سند"),
    ):
        res4 = await read_entire_tool.execute(
            db=db_session,
            context=context,
            conversation=conv,
            document_id="ضابطه773.pdf",
        )
        assert "کل متن سند" in res4.text
        assert res4.citations[0].document_filename == "ضابطه773.pdf"
