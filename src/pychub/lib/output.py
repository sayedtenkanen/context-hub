"""Output formatting utilities (JSON mode + human-friendly with Rich).

Port of cli/src/lib/output.js
"""

import json
import sys
from typing import Any, Callable

from rich.console import Console

console = Console()
stderr_console = Console(stderr=True)


def output(
    data: Any, human_formatter: Callable[[Any], None], opts: dict[str, Any] | None
) -> None:
    """Dual-mode output: JSON or human-friendly.

    Args:
        data: Data to output
        human_formatter: Function to format data for human readability
        opts: Options dict with optional 'json' key
    """
    if opts and opts.get("json"):
        print(json.dumps(data, indent=2))
    else:
        human_formatter(data)


def info(msg: str) -> None:
    """Print informational message to stderr."""
    stderr_console.print(msg)


def error(msg: str, opts: dict[str, Any] | None = None) -> None:
    """Print error and exit.

    Args:
        msg: Error message
        opts: Options dict with optional 'json' key
    """
    if opts and opts.get("json"):
        print(json.dumps({"error": msg}))
    else:
        stderr_console.print(f"Error: {msg}", style="red")
    sys.exit(1)
