"""Update command - refresh the cached registry.

Port of cli/src/commands/update.js
"""

import asyncio

import typer
from rich.console import Console

from ..lib import cache, config, output

console = Console()

update_app = typer.Typer(name="update", help="Refresh the cached registry index")


@update_app.callback(invoke_without_command=True)
def update(
    force: bool = typer.Option(
        False, "--force", help="Force re-download even if cache is fresh"
    ),
    full: bool = typer.Option(
        False, "--full", help="Download the full bundle for offline use"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Refresh the cached registry index."""
    cfg = config.load_config()
    opts = {"json": json_output}

    async def _update() -> None:
        try:
            if full:
                # Download full bundle for each remote source
                for source in cfg["sources"]:
                    if "path" in source:
                        output.info(f"Skipping local source: {source['name']}")
                        continue
                    output.info(f"Downloading full bundle for {source['name']}...")
                    await cache.fetch_full_bundle(source["name"])

                output.output(
                    {"status": "ok", "mode": "full"},
                    lambda d: console.print(
                        "Full bundle(s) downloaded and extracted.", style="green"
                    ),
                    opts,
                )
            else:
                output.info("Updating registries...")
                errors = await cache.fetch_all_registries(force=force)

                if errors:
                    for e in errors:
                        console.print(
                            f"Warning: {e['source']}: {e['error']}",
                            style="yellow",
                            file=console._stderr,
                        )

                updated = len([s for s in cfg["sources"] if "path" not in s]) - len(
                    errors
                )
                output.output(
                    {
                        "status": "ok",
                        "mode": "registry",
                        "updated": updated,
                        "errors": errors,
                    },
                    lambda d: console.print(
                        f"Registry updated ({d['updated']} remote source(s)).",
                        style="green",
                    ),
                    opts,
                )
        except Exception as err:
            output.output(
                {"error": str(err)},
                lambda d: console.print(
                    f"Update failed: {d['error']}", style="red", file=console._stderr
                ),
                opts,
            )
            raise typer.Exit(1)

    asyncio.run(_update())
