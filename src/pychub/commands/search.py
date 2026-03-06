"""search command implementation.

Port of cli/src/commands/search.js
"""

import typer
from rich.console import Console

from ..lib.normalize import display_language
from ..lib.output import output
from ..lib.registry import (
    get_display_id,
    get_entry,
    is_multi_source,
    list_entries,
    search_entries,
)

console = Console()


def format_entry_list(entries: list[dict]) -> None:
    """Format entries as a list."""
    multi = is_multi_source()

    for entry in entries:
        entry_id = get_display_id(entry)
        source = (
            f"[dim][{entry.get('source', '')}][/dim]" if entry.get("source") else ""
        )
        source_name = f"[cyan]({entry['_source']})[/cyan]" if multi else ""
        entry_type = (
            "[magenta][skill][/magenta]"
            if entry.get("_type") == "skill"
            else "[blue][doc][/blue]"
        )
        langs = ", ".join(
            [display_language(l["language"]) for l in entry.get("languages", [])]
        )
        langs_str = f"[dim]{langs}[/dim]" if langs else ""

        desc = entry.get("description", "")
        if desc and len(desc) > 60:
            desc = desc[:57] + "..."

        parts = [
            f"  [bold]{entry_id}[/bold]",
            entry_type,
            langs_str,
            source,
            source_name,
        ]
        console.print(" ".join([p for p in parts if p]).rstrip())

        if desc:
            console.print(f"       [dim]{desc}[/dim]")


def format_entry_detail(entry: dict) -> None:
    """Format a single entry with detail."""
    console.print(f"[bold]{entry['name']}[/bold]")

    if is_multi_source():
        console.print(f"  Source: {entry['_source']}")

    if "source" in entry:
        console.print(f"  Quality: {entry['source']}")

    if "description" in entry:
        console.print(f"  [dim]{entry['description']}[/dim]")

    if entry.get("tags"):
        console.print(f"  Tags: {', '.join(entry['tags'])}")

    console.print()

    if "languages" in entry:
        for lang in entry["languages"]:
            console.print(f"  [bold]{display_language(lang['language'])}[/bold]")
            console.print(f"    Recommended: {lang.get('recommendedVersion', 'N/A')}")
            for v in lang.get("versions", []):
                size = f" ({v['size'] / 1024:.1f} KB)" if v.get("size") else ""
                console.print(
                    f"    {v['version']}{size}  updated: {v.get('lastUpdated', 'N/A')}"
                )
    else:
        # Skill — flat structure
        size = f" ({entry['size'] / 1024:.1f} KB)" if entry.get("size") else ""
        console.print(f"  Path: {entry.get('path', 'N/A')}{size}")
        if "lastUpdated" in entry:
            console.print(f"  Updated: {entry['lastUpdated']}")
        if entry.get("files"):
            console.print(f"  Files: {', '.join(entry['files'])}")


def search_command(
    query: str = typer.Argument(None, help="Search query (omit to list all)"),
    tags: str = typer.Option(None, help="Filter by tags (comma-separated)"),
    lang: str = typer.Option(None, help="Filter by language"),
    limit: int = typer.Option(20, help="Max results"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Search docs and skills (no query lists all).

    Examples:
        pychub search                      # list everything
        pychub search "stripe"            # fuzzy search
        pychub search stripe/payments     # exact id → full detail
        pychub search --tags automation   # filter by tag
    """
    filters = {}
    if tags:
        filters["tags"] = tags
    if lang:
        filters["lang"] = lang

    # No query: list all
    if not query:
        entries = list_entries(filters)[:limit]
        output(
            {"results": entries, "total": len(entries)},
            lambda data: (
                console.print("[yellow]No entries found.[/yellow]")
                if not data["results"]
                else (
                    console.print(f"[bold]{data['total']} entries:\n[/bold]"),
                    format_entry_list(data["results"]),
                )
            ),
            {"json": json},
        )
        return

    # Exact id match: show detail
    result = get_entry(query)

    if result["ambiguous"]:
        output(
            {"error": "ambiguous", "alternatives": result["alternatives"]},
            lambda data: (
                console.print(
                    f'[yellow]Multiple entries with id "{query}". Be specific:[/yellow]'
                ),
                *[
                    console.print(f"  [bold]{alt}[/bold]")
                    for alt in data["alternatives"]
                ],
            ),
            {"json": json},
        )
        return

    if result["entry"]:
        output(result["entry"], format_entry_detail, {"json": json})
        return

    # Fuzzy search
    results = search_entries(query, filters)[:limit]

    output(
        {"results": results, "total": len(results), "query": query},
        lambda data: (
            console.print(f'[yellow]No results for "{query}".[/yellow]')
            if not data["results"]
            else (
                console.print(
                    f'[bold]{data["total"]} results for "{data["query"]}":\n[/bold]'
                ),
                format_entry_list(data["results"]),
            )
        ),
        {"json": json},
    )
