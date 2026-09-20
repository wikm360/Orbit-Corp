import uuid
from datetime import datetime, timezone

from app.features.auth.models import User
from app.features.chat.models import Conversation, ConversationType, Message, SenderType
from app.features.chat.service import list_messages_after


async def test_catch_up_does_not_skip_messages_sharing_a_timestamp(db_session):
    user = User(email="cu@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    conversation = Conversation(type=ConversationType.PERSONAL, created_by=user.id)
    db_session.add(conversation)
    await db_session.flush()

    same_instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    messages = [
        Message(
            id=uuid.UUID(int=i + 1),
            conversation_id=conversation.id,
            sender_type=SenderType.USER,
            content=str(i),
            created_at=same_instant,
        )
        for i in range(3)
    ]
    db_session.add_all(messages)
    await db_session.commit()

    after_first = await list_messages_after(db_session, conversation.id, messages[0].id)
    assert [m.content for m in after_first] == ["1", "2"]

    after_last = await list_messages_after(db_session, conversation.id, messages[2].id)
    assert after_last == []
