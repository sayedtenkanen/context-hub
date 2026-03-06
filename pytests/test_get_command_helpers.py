from pathlib import Path

from pychub.commands.get import _join_parts, _write_output


def test_join_parts_combines_content_and_files() -> None:
    combined = _join_parts(
        [
            {"content": "first"},
            {"files": [{"name": "ref.md", "content": "reference"}]},
        ]
    )

    assert "first" in combined
    assert "# FILE: ref.md" in combined
    assert "reference" in combined


def test_write_output_writes_single_file(tmp_path: Path) -> None:
    out_path = tmp_path / "doc.md"
    _write_output(
        [
            {
                "id": "stripe/api",
                "type": "doc",
                "content": "hello",
                "path": "stripe/docs/DOC.md",
            }
        ],
        str(out_path),
        full=False,
        json_mode=False,
    )

    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8") == "hello"
