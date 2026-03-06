import json

from pychub.commands import feedback as feedback_module


def test_feedback_status_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(feedback_module, "is_telemetry_enabled", lambda: True)
    monkeypatch.setattr(
        feedback_module, "get_telemetry_url", lambda: "https://example.com"
    )
    monkeypatch.setattr(feedback_module, "get_or_create_client_id", lambda: "a" * 64)

    feedback_module.feedback_command(
        status=True,
        json_mode=True,
    )

    captured = capsys.readouterr().out.strip()
    payload = json.loads(captured)
    assert payload["telemetry"] is True
    assert payload["endpoint"] == "https://example.com"
    assert "valid_labels" in payload
