from pathlib import Path

import pychub.lib.config as config_module


def test_load_config_defaults(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CHUB_DIR", str(tmp_path / ".chub"))
    config_module._config = None

    cfg = config_module.load_config()

    assert cfg["sources"] == [{"name": "default", "url": config_module.DEFAULT_CDN_URL}]
    assert cfg["refresh_interval"] == 21600
    assert cfg["telemetry"] is True


def test_load_config_from_file(monkeypatch, tmp_path: Path) -> None:
    chub_dir = tmp_path / ".chub"
    chub_dir.mkdir(parents=True, exist_ok=True)
    (chub_dir / "config.yaml").write_text(
        """
output_dir: .custom-context
refresh_interval: 123
source: official
telemetry: false
sources:
  - name: internal
    path: /tmp/docs
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("CHUB_DIR", str(chub_dir))
    config_module._config = None

    cfg = config_module.load_config()

    assert cfg["output_dir"] == ".custom-context"
    assert cfg["refresh_interval"] == 123
    assert cfg["source"] == "official"
    assert cfg["telemetry"] is False
    assert cfg["sources"] == [{"name": "internal", "path": "/tmp/docs"}]
