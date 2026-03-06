"""Monty runtime integration points for pychub.

This module provides a thin adapter so the CLI can switch from plain Typer
execution to a Monty-orchestrated runtime incrementally.
"""

from __future__ import annotations

import os
from typing import Any


def should_use_monty() -> bool:
    """Return True if monty runtime is explicitly requested."""
    return os.environ.get("PYCHUB_RUNTIME", "").strip().lower() == "monty"


def monty_available() -> bool:
    """Return True if the monty package can be imported."""
    try:
        __import__("monty")
        return True
    except Exception:
        return False


def run_with_monty(app: Any) -> bool:
    """Attempt to run the CLI through a Monty runtime.

    Returns:
        True if execution was handled by Monty, else False.
    """
    if not should_use_monty():
        return False

    if not monty_available():
        # Fallback to Typer if monty is requested but not importable.
        return False

    # TODO: replace this shim with real Monty app composition once
    # pychub command handlers are refactored into Monty workflow components.
    return False
