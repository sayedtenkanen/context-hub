"""feedback command implementation.

Port of cli/src/commands/feedback.js
"""

from __future__ import annotations

import asyncio
from typing import Any

import typer
from rich.console import Console

from .. import get_version
from ..lib.identity import get_or_create_client_id
from ..lib.output import error, output
from ..lib.registry import get_entry
from ..lib.telemetry import get_telemetry_url, is_telemetry_enabled, send_feedback

console = Console()

VALID_LABELS = {
    "accurate",
    "well-structured",
    "helpful",
    "good-examples",
    "outdated",
    "inaccurate",
    "incomplete",
    "wrong-examples",
    "wrong-version",
    "poorly-structured",
}


def feedback_command(
    entry_id: str | None = typer.Argument(None, help="Entry ID to rate"),
    rating: str | None = typer.Argument(None, help="up or down"),
    comment: str | None = typer.Argument(None, help="Optional comment"),
    entry_type: str | None = typer.Option(
        None, "--type", help="Explicit type: doc or skill"
    ),
    lang: str | None = typer.Option(None, "--lang", help="Language variant of the doc"),
    doc_version: str | None = typer.Option(
        None, "--doc-version", help="Version of the doc"
    ),
    file: str | None = typer.Option(
        None, "--file", help="Specific file within the entry"
    ),
    label: list[str] | None = typer.Option(
        None, "--label", help="Feedback label (repeatable)"
    ),
    agent: str | None = typer.Option(None, "--agent", help="AI coding tool name"),
    model: str | None = typer.Option(None, "--model", help="LLM model name"),
    status: bool = typer.Option(False, "--status", help="Show telemetry status"),
    json_mode: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Rate a doc or skill (up/down)."""
    opts = {"json": json_mode}

    if status:
        enabled = is_telemetry_enabled()
        client_id_prefix = None
        try:
            client_id_prefix = get_or_create_client_id()[:8]
        except Exception:
            client_id_prefix = None

        data = {
            "telemetry": enabled,
            "client_id_prefix": client_id_prefix,
            "endpoint": get_telemetry_url(),
            "valid_labels": sorted(VALID_LABELS),
        }

        def human_formatter(payload: dict[str, Any]) -> None:
            console.print(
                f"Telemetry: {'enabled' if payload['telemetry'] else 'disabled'}",
                style="green" if payload["telemetry"] else "red",
            )
            if payload.get("client_id_prefix"):
                console.print(f"Client ID: {payload['client_id_prefix']}...")
            console.print(f"Endpoint:  {payload['endpoint']}")
            console.print(f"Labels:    {', '.join(payload['valid_labels'])}")

        output(data, human_formatter, opts)
        return

    if not entry_id or not rating:
        error(
            "Missing required arguments: <id> and <rating>. Run: pychub feedback <id> <up|down> [comment]",
            opts,
        )

    if rating not in {"up", "down"}:
        error('Rating must be "up" or "down".', opts)

    if not is_telemetry_enabled():
        output(
            {"status": "skipped", "reason": "telemetry_disabled"},
            lambda _: console.print(
                "Telemetry is disabled. Enable with: telemetry: true in ~/.chub/config.yaml",
                style="yellow",
            ),
            opts,
        )
        return

    # Auto-detect entry type if not explicitly set
    detected_type = entry_type
    doc_lang = lang
    doc_ver = doc_version
    source = None

    try:
        result = get_entry(entry_id)
        entry = result.get("entry")
        if entry:
            if not detected_type:
                detected_type = "doc" if "languages" in entry else "skill"
            source = entry.get("_source")

            if entry.get("languages") and not doc_lang and len(entry["languages"]) == 1:
                doc_lang = entry["languages"][0]["language"]

            if entry.get("languages") and not doc_ver:
                lang_obj = None
                if doc_lang:
                    lang_obj = next(
                        (l for l in entry["languages"] if l["language"] == doc_lang),
                        None,
                    )
                if not lang_obj:
                    lang_obj = entry["languages"][0]
                if lang_obj:
                    doc_ver = lang_obj.get("recommendedVersion")
    except Exception:
        # Registry not loaded or other error
        pass

    if not detected_type:
        detected_type = "doc"

    labels = None
    if label:
        normalized = [l.strip().lower() for l in label if l.strip()]
        labels = [l for l in normalized if l in VALID_LABELS]
        if not labels:
            labels = None

    cli_version = get_version()

    result = asyncio.run(
        send_feedback(
            entry_id,
            detected_type,
            rating,
            {
                "comment": comment,
                "docLang": doc_lang,
                "docVersion": doc_ver,
                "targetFile": file,
                "labels": labels,
                "agent": agent,
                "model": model,
                "cliVersion": cli_version,
                "source": source,
            },
        )
    )

    def human_formatter(payload: dict[str, Any]) -> None:
        if payload.get("status") == "sent":
            parts = [f"Feedback recorded for {entry_id}"]
            if doc_lang:
                parts.append(f"lang={doc_lang}")
            if doc_ver:
                parts.append(f"version={doc_ver}")
            if file:
                parts.append(f"file={file}")
            console.print(" ".join(parts), style="green")
        elif payload.get("status") == "error":
            reason = payload.get("reason") or f"HTTP {payload.get('code')}"
            console.print(f"Failed to send feedback: {reason}", style="red")

    output(result, human_formatter, opts)
