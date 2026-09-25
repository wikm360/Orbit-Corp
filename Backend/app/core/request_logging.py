"""Structured request/response logging for the API process console.

The middleware deliberately redacts credentials while keeping ordinary JSON
payloads visible.  It is implemented at the ASGI layer so it also captures
streaming responses without changing their public contract.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import parse_qsl


Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[dict[str, Any], Receive, Send], Awaitable[None]]

logger = logging.getLogger("orbit.traffic")

_SENSITIVE_PARTS = (
    "authorization",
    "cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
)
_REDACTED = "[REDACTED]"


def configure_request_logger(level: int = logging.INFO) -> None:
    """Send traffic logs to stdout once, including under uvicorn."""

    if not any(getattr(handler, "_orbit_traffic_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        handler._orbit_traffic_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def _is_sensitive(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_PARTS)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _REDACTED if _is_sensitive(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _redact_text(value: str) -> str:
    """Best-effort redaction for truncated/malformed JSON and text streams."""

    sensitive_names = "|".join(re.escape(part) for part in _SENSITIVE_PARTS)
    pattern = re.compile(
        rf'(?i)(["\']?[^"\'\s,:=]*(?:{sensitive_names})[^"\'\s,:=]*["\']?\s*[:=]\s*)'
        rf'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[^,\s}}&]+)'
    )
    return pattern.sub(lambda match: f'{match.group(1)}"{_REDACTED}"', value)


def _decode_headers(raw_headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for raw_name, raw_value in raw_headers:
        name = raw_name.decode("latin-1")
        headers[name] = _REDACTED if _is_sensitive(name) else raw_value.decode("latin-1")
    return headers


def _decode_query(raw_query: bytes) -> dict[str, str | list[str]]:
    values: dict[str, str | list[str]] = {}
    for key, value in parse_qsl(raw_query.decode("utf-8", errors="replace"), keep_blank_values=True):
        safe_value = _REDACTED if _is_sensitive(key) else value
        current = values.get(key)
        if current is None:
            values[key] = safe_value
        elif isinstance(current, list):
            current.append(safe_value)
        else:
            values[key] = [current, safe_value]
    return values


def _format_body(data: bytes, content_type: str, total_bytes: int, truncated: bool) -> Any:
    if total_bytes == 0:
        return None

    media_type = content_type.split(";", 1)[0].strip().casefold()
    suffix = f" … [truncated, {total_bytes} bytes total]" if truncated else ""

    if media_type == "multipart/form-data":
        preview = data.decode("latin-1", errors="replace")
        field_names = sorted(set(re.findall(r'name="([^"]+)"', preview)))
        filenames = sorted(set(re.findall(r'filename="([^"]*)"', preview)))
        return {
            "kind": "multipart",
            "size_bytes": total_bytes,
            "fields": [name for name in field_names if not _is_sensitive(name)],
            "redacted_fields": [name for name in field_names if _is_sensitive(name)],
            "filenames": filenames,
            "truncated": truncated,
        }

    text = data.decode("utf-8", errors="replace")
    if media_type == "application/json" or media_type.endswith("+json"):
        try:
            return _redact(json.loads(text))
        except json.JSONDecodeError:
            return {
                "kind": "json-preview",
                "preview": _redact_text(text) + suffix,
                "size_bytes": total_bytes,
                "truncated": truncated,
            }

    if media_type == "application/x-www-form-urlencoded":
        return {
            key: _REDACTED if _is_sensitive(key) else value
            for key, value in parse_qsl(text, keep_blank_values=True)
        }

    if media_type.startswith("text/") or not media_type:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return _redact_text(text) + suffix
        return _redact(parsed)

    return {
        "kind": "binary",
        "content_type": media_type or "application/octet-stream",
        "size_bytes": total_bytes,
        "captured_bytes": len(data),
        "truncated": truncated,
    }


def _write(event: str, payload: dict[str, Any], *, level: int = logging.INFO) -> None:
    logger.log(level, "%s %s", event, json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str))


class RequestResponseLoggingMiddleware:
    """Log every HTTP request and response with correlated structured data."""

    def __init__(self, app: ASGIApp, max_body_bytes: int = 65_536) -> None:
        self.app = app
        self.max_body_bytes = max(0, max_body_bytes)

    async def __call__(self, scope: dict[str, Any], receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        started_at = time.perf_counter()
        raw_headers = list(scope.get("headers", []))
        request_headers = _decode_headers(raw_headers)
        content_type = next(
            (value.decode("latin-1") for name, value in raw_headers if name.lower() == b"content-type"),
            "",
        )

        buffered_messages: list[Message] = []
        request_body = bytearray()
        request_body_bytes = 0
        while True:
            message = await receive()
            buffered_messages.append(message)
            if message["type"] == "http.disconnect":
                break
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            request_body_bytes += len(chunk)
            remaining = self.max_body_bytes - len(request_body)
            if remaining > 0:
                request_body.extend(chunk[:remaining])
            if not message.get("more_body", False):
                break

        client = scope.get("client")
        request_payload = {
            "request_id": request_id,
            "method": scope.get("method"),
            "path": scope.get("path"),
            "query": _decode_query(scope.get("query_string", b"")),
            "client": f"{client[0]}:{client[1]}" if client else None,
            "headers": request_headers,
            "body": _format_body(
                bytes(request_body),
                content_type,
                request_body_bytes,
                request_body_bytes > len(request_body),
            ),
        }
        _write("HTTP_REQUEST", request_payload)

        message_index = 0

        async def replay_receive() -> Message:
            nonlocal message_index
            if message_index < len(buffered_messages):
                message = buffered_messages[message_index]
                message_index += 1
                return message
            return await receive()

        response_status = 500
        response_headers: list[tuple[bytes, bytes]] = []
        response_content_type = ""
        response_body = bytearray()
        response_body_bytes = 0
        response_logged = False

        async def log_response() -> None:
            nonlocal response_logged
            if response_logged:
                return
            response_logged = True
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            payload = {
                "request_id": request_id,
                "method": scope.get("method"),
                "path": scope.get("path"),
                "status": response_status,
                "duration_ms": elapsed_ms,
                "headers": _decode_headers(response_headers),
                "body": _format_body(
                    bytes(response_body),
                    response_content_type,
                    response_body_bytes,
                    response_body_bytes > len(response_body),
                ),
            }
            _write("HTTP_RESPONSE", payload, level=logging.ERROR if response_status >= 500 else logging.INFO)

        async def capture_send(message: Message) -> None:
            nonlocal response_status, response_headers, response_content_type, response_body_bytes
            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = list(message.get("headers", []))
                if not any(name.lower() == b"x-request-id" for name, _ in response_headers):
                    response_headers.append((b"x-request-id", request_id.encode("ascii")))
                    message = {**message, "headers": response_headers}
                response_content_type = next(
                    (value.decode("latin-1") for name, value in response_headers if name.lower() == b"content-type"),
                    "",
                )
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                response_body_bytes += len(chunk)
                remaining = self.max_body_bytes - len(response_body)
                if remaining > 0:
                    response_body.extend(chunk[:remaining])
                if not message.get("more_body", False):
                    await log_response()
            await send(message)

        try:
            await self.app(scope, replay_receive, capture_send)
            await log_response()
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            _write(
                "HTTP_ERROR",
                {
                    "request_id": request_id,
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "duration_ms": elapsed_ms,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                level=logging.ERROR,
            )
            raise
