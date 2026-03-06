from pathlib import Path

from pychub.lib.annotations import (
    clear_annotation,
    list_annotations,
    read_annotation,
    write_annotation,
)


def test_annotation_crud(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CHUB_DIR", str(tmp_path / ".chub"))

    entry_id = "stripe/api"
    assert read_annotation(entry_id) is None

    saved = write_annotation(entry_id, "Use idempotency keys")
    assert saved["id"] == entry_id
    assert saved["note"] == "Use idempotency keys"

    loaded = read_annotation(entry_id)
    assert loaded is not None
    assert loaded["note"] == "Use idempotency keys"

    items = list_annotations()
    assert len(items) == 1
    assert items[0]["id"] == entry_id

    assert clear_annotation(entry_id) is True
    assert read_annotation(entry_id) is None
    assert clear_annotation(entry_id) is False
