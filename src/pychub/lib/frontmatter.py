"""YAML frontmatter parsing.

Port of cli/src/lib/frontmatter.js
"""

import re
from typing import Any

import yaml


def parse_frontmatter(content: str) -> dict[str, Any]:
    """Parse YAML frontmatter from markdown content.

    Returns:
        Dict with 'attributes' (parsed YAML) and 'body' (remaining content)
    """
    match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$", content)
    if not match:
        return {"attributes": {}, "body": content}

    try:
        attributes = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        attributes = {}

    return {"attributes": attributes, "body": match.group(2)}
