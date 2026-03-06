"""Telemetry utilities for pychub feedback.

Port of cli/src/lib/telemetry.js
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from .config import DEFAULT_TELEMETRY_URL, load_config
from .identity import detect_agent, detect_agent_version, get_or_create_client_id


def is_telemetry_enabled() -> bool:
    """Return True if telemetry is enabled via config or env."""
    env_val = os.environ.get("CHUB_TELEMETRY", "").lower()
    if env_val in {"0", "false"}:
        return False
    config = load_config()
    return config.get("telemetry", True) is not False


def get_telemetry_url() -> str:
    """Return telemetry endpoint URL."""
    url = os.environ.get("CHUB_TELEMETRY_URL")
    if url:
        return url
    config = load_config()
    return config.get("telemetry_url") or DEFAULT_TELEMETRY_URL


async def send_feedback(
    entry_id: str, entry_type: str, rating: str, opts: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Send feedback to the API.

    Args:
        entry_id: e.g. "openai/chat"
        entry_type: "doc" or "skill"
        rating: "up" or "down"
        opts: Additional context (docLang, docVersion, targetFile, labels, comment,
              agent, model, cliVersion, source)
    """
    if not is_telemetry_enabled():
        return {"status": "skipped", "reason": "telemetry_disabled"}

    opts = opts or {}

    client_id = get_or_create_client_id()
    telemetry_url = get_telemetry_url()

    payload = {
        "entry_id": entry_id,
        "entry_type": entry_type,
        "rating": rating,
        # Doc-specific dimensions
        "doc_lang": opts.get("docLang") or None,
        "doc_version": opts.get("docVersion") or None,
        "target_file": opts.get("targetFile") or None,
        # Structured feedback
        "labels": opts.get("labels") or None,
        "comment": opts.get("comment") or None,
        # Agent info
        "agent": {
            "name": opts.get("agent") or detect_agent(),
            "version": detect_agent_version(),
            "model": opts.get("model") or None,
        },
        # Context
        "cli_version": opts.get("cliVersion") or None,
        "source": opts.get("source") or None,
    }

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.post(
                f"{telemetry_url}/feedback",
                headers={
                    "Content-Type": "application/json",
                    "X-Client-ID": client_id,
                },
                json=payload,
            )

        if res.status_code >= 200 and res.status_code < 300:
            data = res.json()
            return {
                "status": "sent",
                "feedback_id": data.get("feedback_id") or data.get("id"),
            }

        return {"status": "error", "code": res.status_code}
    except Exception:
        return {"status": "error", "reason": "network"}
