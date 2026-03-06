from pathlib import Path

import pychub.lib.cache as cache


def test_clear_cache_preserves_config(monkeypatch, tmp_path: Path) -> None:
    chub_dir = tmp_path / ".chub"
    chub_dir.mkdir(parents=True, exist_ok=True)
    config_path = chub_dir / "config.yaml"
    config_path.write_text("telemetry: false\n", encoding="utf-8")

    monkeypatch.setenv("CHUB_DIR", str(chub_dir))

    cache.clear_cache()

    assert config_path.exists()
    assert "telemetry: false" in config_path.read_text(encoding="utf-8")


def test_get_cache_stats_with_remote_source(monkeypatch, tmp_path: Path) -> None:
    chub_dir = tmp_path / ".chub"
    data_dir = chub_dir / "sources" / "default" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "doc.md").write_text("content", encoding="utf-8")

    monkeypatch.setenv("CHUB_DIR", str(chub_dir))

    def _load_config():
        return {"sources": [{"name": "default", "url": "https://example.com"}]}

    monkeypatch.setattr(cache, "load_config", _load_config)

    stats = cache.get_cache_stats()
    assert stats["exists"] is True
    assert stats["sources"][0]["type"] == "remote"
    assert stats["sources"][0]["fileCount"] == 1
