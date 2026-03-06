"""Machine identity and agent detection.

Port of cli/src/lib/identity.js
"""

import hashlib
import os
import platform
import subprocess
from pathlib import Path

from .config import get_chub_dir

_cached_client_id: str | None = None


def get_machine_uuid() -> str:
    """Get the platform-native machine UUID."""
    plat = platform.system()

    if plat == "Darwin":
        result = subprocess.run(
            [
                "ioreg",
                "-rd1",
                "-c",
                "IOPlatformExpertDevice",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # Parse for IOPlatformUUID
        for line in result.stdout.splitlines():
            if "IOPlatformUUID" in line:
                # Extract UUID from: "IOPlatformUUID" = "xxx-xxx-xxx"
                parts = line.split('"')
                if len(parts) >= 4:
                    return parts[3]
        raise RuntimeError("Could not find IOPlatformUUID")

    if plat == "Linux":
        try:
            return Path("/etc/machine-id").read_text().strip()
        except FileNotFoundError:
            return Path("/var/lib/dbus/machine-id").read_text().strip()

    if plat == "Windows":
        result = subprocess.run(
            [
                "reg",
                "query",
                r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography",
                "/v",
                "MachineGuid",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.splitlines():
            if "MachineGuid" in line:
                parts = line.split()
                if len(parts) >= 3:
                    return parts[-1].strip()
        raise RuntimeError("Could not parse MachineGuid from registry")

    raise RuntimeError(f"Unsupported platform: {plat}")


def get_or_create_client_id() -> str:
    """Get or create a stable, anonymous client ID.

    Checks ~/.chub/client_id for a cached 64-char hex string.
    If not found, hashes the machine UUID with SHA-256 and saves it.
    """
    global _cached_client_id
    if _cached_client_id:
        return _cached_client_id

    chub_dir = get_chub_dir()
    id_path = chub_dir / "client_id"

    # Try to read existing client id
    if id_path.exists():
        existing = id_path.read_text().strip()
        if len(existing) == 64 and all(c in "0123456789abcdef" for c in existing):
            _cached_client_id = existing
            return existing

    # Generate from machine UUID
    uuid = get_machine_uuid()
    hash_obj = hashlib.sha256(uuid.encode())
    client_id = hash_obj.hexdigest()

    # Ensure directory exists
    chub_dir.mkdir(parents=True, exist_ok=True)
    id_path.write_text(client_id, encoding="utf-8")

    _cached_client_id = client_id
    return client_id


def detect_agent() -> str:
    """Auto-detect the AI coding tool from environment variables."""
    if os.getenv("CLAUDE_CODE") or os.getenv("CLAUDE_SESSION_ID"):
        return "claude-code"
    if os.getenv("CURSOR_SESSION_ID") or os.getenv("CURSOR_TRACE_ID"):
        return "cursor"
    if os.getenv("CODEX_HOME") or os.getenv("CODEX_SESSION"):
        return "codex"
    if os.getenv("WINDSURF_SESSION"):
        return "windsurf"
    if os.getenv("AIDER_MODEL") or os.getenv("AIDER"):
        return "aider"
    if os.getenv("CLINE_SESSION"):
        return "cline"
    if os.getenv("GITHUB_COPILOT"):
        return "copilot"
    return "unknown"


def detect_agent_version() -> str | None:
    """Detect the version of the AI coding tool, if available."""
    return os.getenv("CLAUDE_CODE_VERSION") or os.getenv("CURSOR_VERSION")
