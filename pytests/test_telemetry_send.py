from __future__ import annotations

from typing import Any

import pychub.lib.telemetry as telemetry


class _StubResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self._payload


class _StubClient:
    def __init__(self, response: _StubResponse) -> None:
        self._response = response

    async def __aenter__(self) -> "_StubClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(
        self, url: str, headers: dict[str, str], json: dict[str, Any]
    ) -> _StubResponse:
        return self._response


def test_send_feedback_disabled(monkeypatch) -> None:
    monkeypatch.setattr(telemetry, "is_telemetry_enabled", lambda: False)
    assert telemetry.is_telemetry_enabled() is False

    import asyncio

    result = asyncio.run(telemetry.send_feedback("openai/chat", "doc", "up", {}))
    assert result["status"] == "skipped"
    assert result["reason"] == "telemetry_disabled"


def test_send_feedback_success(monkeypatch) -> None:
    monkeypatch.setattr(telemetry, "is_telemetry_enabled", lambda: True)
    monkeypatch.setattr(telemetry, "get_or_create_client_id", lambda: "b" * 64)
    monkeypatch.setattr(telemetry, "detect_agent", lambda: "test-agent")
    monkeypatch.setattr(telemetry, "detect_agent_version", lambda: "0.0")

    async def _run() -> dict[str, Any]:
        response = _StubResponse(200, {"feedback_id": "fb-123"})
        monkeypatch.setattr(
            telemetry,
            "httpx",
            type("X", (), {"AsyncClient": lambda **_: _StubClient(response)}),
        )
        return await telemetry.send_feedback("openai/chat", "doc", "up", {})

    import asyncio

    result = asyncio.run(_run())
    assert result["status"] == "sent"
    assert result["feedback_id"] == "fb-123"


def test_send_feedback_error_code(monkeypatch) -> None:
    monkeypatch.setattr(telemetry, "is_telemetry_enabled", lambda: True)
    monkeypatch.setattr(telemetry, "get_or_create_client_id", lambda: "c" * 64)

    async def _run() -> dict[str, Any]:
        response = _StubResponse(503, {})
        monkeypatch.setattr(
            telemetry,
            "httpx",
            type("X", (), {"AsyncClient": lambda **_: _StubClient(response)}),
        )
        return await telemetry.send_feedback("openai/chat", "doc", "down", {})

    import asyncio

    result = asyncio.run(_run())
    assert result["status"] == "error"
    assert result["code"] == 503
