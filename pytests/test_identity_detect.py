import os

from pychub.lib.identity import detect_agent, detect_agent_version


def test_detect_agent_envs(monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE", "1")
    assert detect_agent() == "claude-code"

    monkeypatch.delenv("CLAUDE_CODE", raising=False)
    monkeypatch.setenv("CURSOR_SESSION_ID", "1")
    assert detect_agent() == "cursor"

    monkeypatch.delenv("CURSOR_SESSION_ID", raising=False)
    monkeypatch.setenv("GITHUB_COPILOT", "1")
    assert detect_agent() == "copilot"

    monkeypatch.delenv("GITHUB_COPILOT", raising=False)
    assert detect_agent() == "unknown"


def test_detect_agent_version(monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_VERSION", "1.2.3")
    assert detect_agent_version() == "1.2.3"

    monkeypatch.delenv("CLAUDE_CODE_VERSION", raising=False)
    monkeypatch.setenv("CURSOR_VERSION", "9.9.9")
    assert detect_agent_version() == "9.9.9"
