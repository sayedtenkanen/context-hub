"""Local annotation storage and management.

Port of cli/src/lib/annotations.js
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from .config import get_chub_dir


def get_annotations_dir() -> Path:
    """Get the annotations directory (~/.chub/annotations)."""
    return get_chub_dir() / "annotations"


def annotation_path(entry_id: str) -> Path:
    """Get the path for a specific entry's annotation file."""
    safe = entry_id.replace("/", "--")
    return get_annotations_dir() / f"{safe}.json"


def read_annotation(entry_id: str) -> dict | None:
    """Read annotation for an entry, or None if not found."""
    try:
        path = annotation_path(entry_id)
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def write_annotation(entry_id: str, note: str) -> dict:
    """Write an annotation for an entry."""
    annotations_dir = get_annotations_dir()
    annotations_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "id": entry_id,
        "note": note,
        "updatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }

    path = annotation_path(entry_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return data


def clear_annotation(entry_id: str) -> bool:
    """Remove annotation for an entry. Returns True if removed, False if not found."""
    try:
        annotation_path(entry_id).unlink()
        return True
    except FileNotFoundError:
        return False


def list_annotations() -> list[dict]:
    """List all annotations."""
    annotations_dir = get_annotations_dir()
    if not annotations_dir.exists():
        return []

    annotations = []
    for path in annotations_dir.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                annotations.append(json.load(f))
        except Exception:
            # Skip invalid files
            continue

    return annotations
