"""annotate command implementation.

Port of cli/src/commands/annotate.js
"""

import typer
from rich.console import Console

from ..lib.annotations import clear_annotation, list_annotations, read_annotation, write_annotation
from ..lib.output import error, output

console = Console()


def annotate_command(
    entry_id: str = typer.Argument(None, help="Entry ID to annotate"),
    note: str = typer.Argument(None, help="Annotation text"),
    clear: bool = typer.Option(False, "--clear", help="Remove annotation for this entry"),
    list_all: bool = typer.Option(False, "--list", help="List all annotations"),
    json: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Attach agent notes to a doc or skill.

    Examples:
        pychub annotate stripe/api "Use idempotency keys for POST requests"
        pychub annotate stripe/api           # view current note
        pychub annotate stripe/api --clear   # remove
        pychub annotate --list               # list all
    """
    opts = {"json": json}

    if list_all:
        annotations = list_annotations()
        output(
            annotations,
            lambda data: (
                console.print("No annotations.")
                if not data
                else *[
                    (
                        console.print(f"[bold]{a['id']}[/bold] [dim]({a['updatedAt']})[/dim]"),
                        console.print(f"  {a['note']}\n"),
                    )
                    for a in data
                ],
            ),
            opts,
        )
        return

    if not entry_id:
        error(
            "Missing required argument: <id>. Run: pychub annotate <id> <note> | pychub annotate <id> --clear | pychub annotate --list",
            opts,
        )

    if clear:
        removed = clear_annotation(entry_id)
        output(
            {"id": entry_id, "cleared": removed},
            lambda data: console.print(
                f"Annotation cleared for [bold]{data['id']}[/bold]."
                if data["cleared"]
                else f"No annotation found for [bold]{data['id']}[/bold]."
            ),
            opts,
        )
        return

    if not note:
        # Show existing annotation
        existing = read_annotation(entry_id)
        if existing:
            output(
                existing,
                lambda data: (
                    console.print(f"[bold]{data['id']}[/bold] [dim]({data['updatedAt']})[/dim]"),
                    console.print(data["note"]),
                ),
                opts,
            )
        else:
            output(
                {"id": entry_id, "note": None},
                lambda _: console.print(f"No annotation for [bold]{entry_id}[/bold]."),
                opts,
            )
        return

    data = write_annotation(entry_id, note)
    output(
        data,
        lambda d: console.print(f"Annotation saved for [bold]{d['id']}[/bold]."),
        opts,
    )
