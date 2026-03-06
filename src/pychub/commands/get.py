"""get command implementation.

Port of cli/src/commands/get.js
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import typer

from ..lib.annotations import read_annotation
from ..lib.cache import fetch_doc, fetch_doc_full
from ..lib.output import error, info, output
from ..lib.registry import get_entry, resolve_doc_path, resolve_entry_file


def _join_parts(results: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in results:
        if "files" in item:
            for f in item["files"]:
                parts.append(f"# FILE: {f['name']}\n\n{f['content']}")
        else:
            parts.append(item["content"])
    return "\n\n---\n\n".join(parts)


async def _fetch_entries(
    ids: list[str],
    lang: str | None,
    version: str | None,
    full: bool,
    file: str | None,
    global_opts: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for entry_id in ids:
        result = get_entry(entry_id)

        if result["ambiguous"]:
            alternatives = "\n  ".join(
                [f"pychub get {a}" for a in result["alternatives"]]
            )
            error(
                f'Multiple entries match "{entry_id}". Use a source prefix:\n  {alternatives}',
                global_opts,
            )

        if not result["entry"]:
            error(f'No doc or skill found with id "{entry_id}".', global_opts)

        entry = result["entry"]
        entry_type = "doc" if "languages" in entry else "skill"
        resolved = resolve_doc_path(entry, lang, version)

        if not resolved:
            if lang and "languages" in entry:
                available = ", ".join(
                    [lang_item["language"] for lang_item in entry["languages"]]
                )
                error(
                    f'Language "{lang}" is not available for "{entry_id}". Available languages: {available}.',
                    global_opts,
                )
            error(f'No content found for "{entry_id}".', global_opts)

        assert resolved is not None

        if resolved.get("versionNotFound"):
            available = ", ".join(resolved.get("available", []))
            error(
                f'Version "{resolved.get("requested")}" not found for "{entry_id}". Available versions: {available}',
                global_opts,
            )

        if resolved.get("needsLanguage"):
            available = ", ".join(resolved.get("available", []))
            error(
                f'Multiple languages available for "{entry_id}": {available}. Specify --lang.',
                global_opts,
            )

        entry_file = resolve_entry_file(resolved, entry_type)
        if entry_file.get("error"):
            error(
                f'No content available for "{entry_id}". Run `pychub update` to refresh remote registries.',
                global_opts,
            )

        entry_filename = "SKILL.md" if entry_type == "skill" else "DOC.md"
        ref_files = [f for f in resolved.get("files", []) if f != entry_filename]

        try:
            if file:
                requested = [f.strip() for f in file.split(",") if f.strip()]
                invalid = [f for f in requested if f not in resolved.get("files", [])]
                if invalid:
                    available = ", ".join(ref_files) if ref_files else "(none)"
                    error(
                        f'File "{invalid[0]}" not found in {entry_id}. Available: {available}',
                        global_opts,
                    )

                if len(requested) == 1:
                    doc_content = await fetch_doc(
                        resolved["source"], f"{resolved['path']}/{requested[0]}"
                    )
                    results.append(
                        {
                            "id": entry["id"],
                            "type": entry_type,
                            "content": doc_content,
                            "path": f"{resolved['path']}/{requested[0]}",
                        }
                    )
                else:
                    all_files = await fetch_doc_full(
                        resolved["source"], resolved["path"], requested
                    )
                    results.append(
                        {
                            "id": entry["id"],
                            "type": entry_type,
                            "files": all_files,
                            "path": resolved["path"],
                        }
                    )
            elif full and resolved.get("files"):
                all_files = await fetch_doc_full(
                    resolved["source"], resolved["path"], resolved["files"]
                )
                results.append(
                    {
                        "id": entry["id"],
                        "type": entry_type,
                        "files": all_files,
                        "path": resolved["path"],
                    }
                )
            else:
                doc_content = await fetch_doc(
                    resolved["source"], entry_file["filePath"]
                )
                results.append(
                    {
                        "id": entry["id"],
                        "type": entry_type,
                        "content": doc_content,
                        "path": entry_file["filePath"],
                        "additionalFiles": ref_files,
                    }
                )
        except Exception as exc:
            error(f'Failed to load "{entry_id}": {exc}', global_opts)

    return results


def _write_output(
    results: list[dict[str, Any]], output_path: str, full: bool, json_mode: bool
) -> None:
    out = Path(output_path)

    if full:
        for item in results:
            if "files" in item:
                base_dir = out / item["id"] if len(results) > 1 else out
                base_dir.mkdir(parents=True, exist_ok=True)
                for f in item["files"]:
                    dest = base_dir / f["name"]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(f["content"], encoding="utf-8")
                info(f"Written {len(item['files'])} files to {base_dir}")
            else:
                dest = out / f"{item['id']}.md"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(item["content"], encoding="utf-8")
                info(f"Written to {dest}")

        if json_mode:
            output(
                [
                    {"id": item["id"], "type": item["type"], "path": output_path}
                    for item in results
                ],
                lambda _: None,
                {"json": True},
            )
        return

    is_dir = output_path.endswith("/") or (out.exists() and out.is_dir())
    if is_dir and len(results) > 1:
        out.mkdir(parents=True, exist_ok=True)
        for item in results:
            dest = out / f"{item['id']}.md"
            content = _join_parts([item])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            info(f"Written to {dest}")
    else:
        dest = out / f"{results[0]['id']}.md" if is_dir else out
        dest.parent.mkdir(parents=True, exist_ok=True)
        combined = _join_parts(results)
        dest.write_text(combined, encoding="utf-8")
        info(f"Written to {dest}")

    if json_mode:
        output(
            [
                {"id": item["id"], "type": item["type"], "path": output_path}
                for item in results
            ],
            lambda _: None,
            {"json": True},
        )


def get_command(
    ids: list[str] = typer.Argument(..., help="One or more entry IDs"),
    lang: str | None = typer.Option(None, "--lang", help="Language variant (for docs)"),
    version: str | None = typer.Option(
        None, "--version", help="Specific version (for docs)"
    ),
    output_path: str | None = typer.Option(
        None, "-o", "--output", help="Write to file or directory"
    ),
    full: bool = typer.Option(
        False, "--full", help="Fetch all files (not just entry point)"
    ),
    file: str | None = typer.Option(
        None, "--file", help="Fetch specific file(s) by path (comma-separated)"
    ),
    json_mode: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Fetch docs or skills by ID (auto-detects type)."""
    opts = {"json": json_mode}

    results = asyncio.run(_fetch_entries(ids, lang, version, full, file, opts))

    if output_path:
        _write_output(results, output_path, full, json_mode)
        return

    if len(results) == 1 and "files" not in results[0]:
        item = results[0]
        annotation = read_annotation(item["id"])
        extra_files = item.get("additionalFiles", [])

        data: dict[str, Any] = {
            "id": item["id"],
            "type": item["type"],
            "content": item["content"],
            "path": item["path"],
        }
        if extra_files:
            data["additionalFiles"] = extra_files
        if annotation:
            data["annotation"] = annotation

        def human_formatter(payload: dict[str, Any]) -> None:
            print(payload["content"], end="")
            if annotation:
                print(
                    f"\n\n---\n[Agent note — {annotation['updatedAt']}]\n{annotation['note']}\n",
                    end="",
                )
            if extra_files:
                file_list = "\n".join([f"  {f}" for f in extra_files])
                example = f"pychub get {item['id']} --file {extra_files[0]}"
                print(
                    f"\n\n---\nAdditional files available (use --file to fetch):\n{file_list}\nExample: {example}\n",
                    end="",
                )

        output(data, human_formatter, opts)
        return

    combined = _join_parts(results)

    output(
        [
            {"id": item["id"], "type": item["type"], "path": item["path"]}
            for item in results
        ],
        lambda _: print(combined, end=""),
        opts,
    )
