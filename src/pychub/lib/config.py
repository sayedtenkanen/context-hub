"""Configuration management for pychub.

Port of cli/src/lib/config.js
"""

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CDN_URL = "https://cdn.aichub.org/v1"
DEFAULT_TELEMETRY_URL = "https://api.aichub.org/v1"

DEFAULTS = {
    "output_dir": ".context",
    "refresh_interval": 21600,  # 6 hours
    "output_format": "human",
    "source": "official,maintainer,community",
    "telemetry": True,
    "telemetry_url": DEFAULT_TELEMETRY_URL,
}

_config: dict[str, Any] | None = None


def get_chub_dir() -> Path:
    """Get the chub config directory (~/.chub)."""
    import os

    return Path(os.environ.get("CHUB_DIR", Path.home() / ".chub"))


def load_config() -> dict[str, Any]:
    """Load configuration from ~/.chub/config.yaml with defaults."""
    global _config
    if _config is not None:
        return _config

    file_config: dict[str, Any] = {}
    config_path = get_chub_dir() / "config.yaml"

    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                file_config = yaml.safe_load(f) or {}
        except Exception:
            # No config file or parse error, use defaults
            pass

    # Build sources list
    if "sources" in file_config and isinstance(file_config["sources"], list):
        sources = file_config["sources"]
    else:
        # Backward compat: single cdn_url becomes a single source
        import os

        url = os.environ.get("CHUB_BUNDLE_URL") or file_config.get(
            "cdn_url", DEFAULT_CDN_URL
        )
        sources = [{"name": "default", "url": url}]

    _config = {
        "sources": sources,
        "output_dir": file_config.get("output_dir", DEFAULTS["output_dir"]),
        "refresh_interval": file_config.get(
            "refresh_interval", DEFAULTS["refresh_interval"]
        ),
        "output_format": file_config.get("output_format", DEFAULTS["output_format"]),
        "source": file_config.get("source", DEFAULTS["source"]),
        "telemetry": file_config.get("telemetry", DEFAULTS["telemetry"]),
        "telemetry_url": file_config.get("telemetry_url", DEFAULTS["telemetry_url"]),
    }

    return _config
