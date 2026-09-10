import asyncio
import json
import uuid

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()


def _channel(conversation_id: uuid.UUID) -> str:
    return f"conversation:{conversation_id}"


class ConnectionManager:
    """Fans conversation events out to connected websockets via Redis pub/sub.

    Publishing through Redis (rather than an in-process dict of sockets)
    means it works correctly if the backend ever runs as more than one
    process/instance: whichever instance holds a given browser's socket
    still receives events published by another instance.
    """

    def __init__(self) -> None:
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._connections: dict[uuid.UUID, set] = {}
        self._listeners: dict[uuid.UUID, asyncio.Task] = {}

    async def connect(self, conversation_id: uuid.UUID, websocket) -> None:
        await websocket.accept()
        self._connections.setdefault(conversation_id, set()).add(websocket)
        if conversation_id not in self._listeners:
            self._listeners[conversation_id] = asyncio.create_task(self._listen(conversation_id))

    async def disconnect(self, conversation_id: uuid.UUID, websocket) -> None:
        conns = self._connections.get(conversation_id)
        if conns is None:
            return
        conns.discard(websocket)
        if not conns:
            self._connections.pop(conversation_id, None)
            task = self._listeners.pop(conversation_id, None)
            if task is not None:
                task.cancel()

    async def broadcast(self, conversation_id: uuid.UUID, event: dict) -> None:
        await self._redis.publish(_channel(conversation_id), json.dumps(event, default=str))

    async def _listen(self, conversation_id: uuid.UUID) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(_channel(conversation_id))
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                for ws in list(self._connections.get(conversation_id, ())):
                    try:
                        await ws.send_text(message["data"])
                    except Exception:
                        pass
        finally:
            await pubsub.unsubscribe(_channel(conversation_id))
            await pubsub.close()


manager = ConnectionManager()
