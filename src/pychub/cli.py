"""CLI entrypoint for pychub."""

import asyncio

import typer

from . import get_version
from .commands.annotate import annotate_command
from .commands.cache import cache_app
from .commands.get import get_command
from .commands.search import search_command
from .commands.update import update_command
from .lib.cache import ensure_registry
from .lib.output import error
from .runtime.monty_runtime import run_with_monty

app = typer.Typer(add_completion=False, no_args_is_help=False)

# Commands that can run without a loaded registry
SKIP_REGISTRY = {"update", "cache", "annotate"}


def version_callback(value: bool) -> None:
    if value:
        typer.echo(get_version())
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """pychub — Context Hub CLI v{version}

    Search and retrieve LLM-optimized docs and skills.
    """
    if not ctx.invoked_subcommand:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    if ctx.invoked_subcommand in SKIP_REGISTRY:
        return

    try:
        asyncio.run(ensure_registry())
    except Exception as e:
        error(
            f"Registry not available: {e}. Run `pychub update` to refresh remote registries, or check that local source paths in ~/.chub/config.yaml are correct.",
            {},
        )


# Register commands
app.command(name="search", help="Search docs and skills (no query lists all)")(
    search_command
)
app.command(name="get", help="Fetch docs or skills by ID")(get_command)
app.command(name="update", help="Refresh the cached registry index")(update_command)
app.command(name="annotate", help="Attach agent notes to a doc or skill")(
    annotate_command
)
app.add_typer(cache_app, name="cache")


def main() -> None:
    if run_with_monty(app):
        return
    app()


if __name__ == "__main__":
    main()
