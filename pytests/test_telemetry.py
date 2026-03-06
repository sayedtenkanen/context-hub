from pychub.lib.telemetry import get_telemetry_url, is_telemetry_enabled


def test_is_telemetry_enabled_env_off(monkeypatch) -> None:
    monkeypatch.setenv("CHUB_TELEMETRY", "0")
    assert is_telemetry_enabled() is False


def test_get_telemetry_url_env_override(monkeypatch) -> None:
    monkeypatch.setenv("CHUB_TELEMETRY_URL", "https://example.com")
    assert get_telemetry_url() == "https://example.com"
