"""Cache command - manage the local cache.

Port of cli/src/commands/cache.js
"""

import typer
from rich.console import Console

from ..lib import cache, output

console = Console()

cache_app = typer.Typer(name="cache", help="Manage the local cache")


@cache_app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show cache information."""
    opts = {"json": json_output}
    stats = cache.get_cache_stats()

    def human_formatter(s: dict) -> None:
        if not s["exists"] or not s["sources"]:
            console.print(
                "No cache found. Run `pychub update` to initialize.", style="yellow"
            )
            return

        console.print("[bold]Cache Status[/bold]\n")
        for src in s["sources"]:
            if src["type"] == "local":
                console.print(f"  [bold]{src['name']}[/bold] [dim](local)[/dim]")
                console.print(f"    Path: {src['path']}")
            else:
                console.print(f"  [bold]{src['name']}[/bold] [dim](remote)[/dim]")
                has_reg = (
                    "[green]yes[/green]" if src["hasRegistry"] else "[red]no[/red]"
                )
                console.print(f"    Registry: {has_reg}")
                console.print(f"    Last updated: {src['lastUpdated'] or 'never'}")
                console.print(
                    f"    Full bundle: {'yes' if src['fullBundle'] else 'no'}"
                )
                console.print(f"    Cached files: {src['fileCount']}")
                console.print(f"    Size: {src['dataSize'] / 1024:.1f} KB")

    output.output(stats, human_formatter, opts)


@cache_app.command("clear")
def clear(
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Clear cached data."""
    opts = {"json": json_output}

    if not force and not json_output:
        confirm = typer.confirm("Clear all cached data?")
        if not confirm:
            raise typer.Abort()

    cache.clear_cache()
    output.output(
        {"status": "cleared"},
        lambda d: console.print("Cache cleared.", style="green"),
        opts,
    )
