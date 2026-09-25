import io
import json
import logging

from app.core.request_logging import RequestResponseLoggingMiddleware, _format_body, logger


def test_truncated_json_preview_does_not_leak_sensitive_values():
    body = b'{"password":"do-not-log","message":"a long value that is cut'
    formatted = _format_body(body[:42], "application/json", len(body), truncated=True)
    rendered = json.dumps(formatted)
    assert "do-not-log" not in rendered
    assert "[REDACTED]" in rendered


async def test_request_response_logging_redacts_secrets_and_correlates_events():
    async def demo_app(scope, receive, send):
        request = await receive()
        payload = json.loads(request["body"])
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
        await send({
            "type": "http.response.body",
            "body": json.dumps({"email": payload["email"], "access_token": "server-secret"}).encode(),
        })

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    original_handlers = list(logger.handlers)
    original_level = logger.level
    original_propagate = logger.propagate
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    incoming = [{
        "type": "http.request",
        "body": json.dumps({"email": "user@example.com", "password": "client-secret"}).encode(),
        "more_body": False,
    }]
    sent = []

    async def receive():
        return incoming.pop(0)

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "query_string": b"refresh_token=query-secret",
        "headers": [(b"content-type", b"application/json"), (b"authorization", b"Bearer header-secret")],
        "client": ("127.0.0.1", 1234),
    }

    try:
        await RequestResponseLoggingMiddleware(demo_app)(scope, receive, send)
    finally:
        logger.handlers = original_handlers
        logger.setLevel(original_level)
        logger.propagate = original_propagate

    output = stream.getvalue()
    assert "HTTP_REQUEST" in output
    assert "HTTP_RESPONSE" in output
    assert output.count("request_id") == 2
    assert "user@example.com" in output
    assert "client-secret" not in output
    assert "server-secret" not in output
    assert "query-secret" not in output
    assert "header-secret" not in output
    assert output.count("[REDACTED]") >= 4
    response_start = next(message for message in sent if message["type"] == "http.response.start")
    assert any(name == b"x-request-id" for name, _ in response_start["headers"])
