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
        self._subscribed: dict[uuid.UUID, asyncio.Event] = {}

    async def connect(self, conversation_id: uuid.UUID, websocket) -> None:
        # Subscribe to Redis *before* accepting: once the client sees the
        # socket open it may assume nothing published from then on is missed.
        await self._ensure_listener(conversation_id)
        try:
            await websocket.accept()
        except BaseException:
            self._stop_listener_if_idle(conversation_id)
            raise
        self._connections.setdefault(conversation_id, set()).add(websocket)

    async def disconnect(self, conversation_id: uuid.UUID, websocket) -> None:
        conns = self._connections.get(conversation_id)
        if conns is not None:
            conns.discard(websocket)
            if not conns:
                self._connections.pop(conversation_id, None)
        self._stop_listener_if_idle(conversation_id)

    async def broadcast(self, conversation_id: uuid.UUID, event: dict) -> None:
        await self._redis.publish(_channel(conversation_id), json.dumps(event, default=str))

    async def _ensure_listener(self, conversation_id: uuid.UUID) -> None:
        task = self._listeners.get(conversation_id)
        if task is None or task.done():
            ready = asyncio.Event()
            self._subscribed[conversation_id] = ready
            self._listeners[conversation_id] = asyncio.create_task(
                self._listen(conversation_id, ready)
            )
        await self._subscribed[conversation_id].wait()

    def _stop_listener_if_idle(self, conversation_id: uuid.UUID) -> None:
        if self._connections.get(conversation_id):
            return
        task = self._listeners.pop(conversation_id, None)
        self._subscribed.pop(conversation_id, None)
        if task is not None:
            task.cancel()

    async def _listen(self, conversation_id: uuid.UUID, ready: asyncio.Event) -> None:
        pubsub = self._redis.pubsub()
        try:
            await pubsub.subscribe(_channel(conversation_id))
            ready.set()
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                for ws in list(self._connections.get(conversation_id, ())):
                    try:
                        await ws.send_text(message["data"])
                    except Exception:
                        pass
        finally:
            # Unblock any connect() still waiting if subscribing itself failed.
            ready.set()
            await pubsub.unsubscribe(_channel(conversation_id))
            await pubsub.close()


manager = ConnectionManager()


async def publish_event(conversation_id: uuid.UUID, event: dict) -> None:
    """One-shot publish onto a conversation's channel, for callers outside
    the main app process (the RQ ingestion worker, which runs each job in
    its own fresh event loop via `asyncio.run`). `manager.broadcast` reuses
    a single long-lived Redis client tied to whichever loop first used it -
    fine for the main process's one event loop, but unsafe to reuse across
    the worker's many short-lived ones. This opens and closes its own
    connection instead."""
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis_client.publish(_channel(conversation_id), json.dumps(event, default=str))
    finally:
        await redis_client.aclose()
