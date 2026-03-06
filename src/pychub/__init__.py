"""Python implementation of the Context Hub CLI."""

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """Return the installed package version or a fallback."""
    try:
        return version("pychub")
    except PackageNotFoundError:
        return "0.0.0"


__all__ = ["get_version"]
