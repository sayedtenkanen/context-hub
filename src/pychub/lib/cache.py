"""Cache management and registry fetching.

Port of cli/src/lib/cache.js
"""

import json
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from .config import get_chub_dir, load_config


def get_bundled_dir() -> Path:
    """Path to bundled content shipped with the package."""
    # Will contain registry.json + doc files built at publish time
    return Path(__file__).parent.parent.parent.parent / "cli" / "dist"


def get_source_dir(source_name: str) -> Path:
    """Get cache directory for a specific source."""
    return get_chub_dir() / "sources" / source_name


def get_source_data_dir(source_name: str) -> Path:
    """Get data directory for a specific source."""
    return get_source_dir(source_name) / "data"


def get_source_meta_path(source_name: str) -> Path:
    """Get meta.json path for a source."""
    return get_source_dir(source_name) / "meta.json"


def get_source_registry_path(source_name: str) -> Path:
    """Get registry.json path for a source."""
    return get_source_dir(source_name) / "registry.json"


def read_meta(source_name: str) -> dict[str, Any]:
    """Read metadata for a source."""
    path = get_source_meta_path(source_name)
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_meta(source_name: str, meta: dict[str, Any]) -> None:
    """Write metadata for a source."""
    dir_path = get_source_dir(source_name)
    dir_path.mkdir(parents=True, exist_ok=True)
    path = get_source_meta_path(source_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def is_source_cache_fresh(source_name: str) -> bool:
    """Check if a source's cache is fresh."""
    meta = read_meta(source_name)
    if "lastUpdated" not in meta:
        return False

    config = load_config()
    age = datetime.now().timestamp() - meta["lastUpdated"] / 1000
    return age < config["refresh_interval"]


async def fetch_remote_registry(source: dict[str, Any], force: bool = False) -> None:
    """Fetch registry for a single remote source."""
    source_name = source["name"]

    if not force and is_source_cache_fresh(source_name):
        registry_path = get_source_registry_path(source_name)
        if registry_path.exists():
            return

    url = f"{source['url']}/registry.json"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()

        data = response.text
        dir_path = get_source_dir(source_name)
        dir_path.mkdir(parents=True, exist_ok=True)

        registry_path = get_source_registry_path(source_name)
        registry_path.write_text(data, encoding="utf-8")

        meta = read_meta(source_name)
        meta["lastUpdated"] = int(datetime.now().timestamp() * 1000)
        write_meta(source_name, meta)


async def fetch_all_registries(force: bool = False) -> list[dict[str, str]]:
    """Fetch registries for all configured sources.

    Returns list of errors (empty if all succeeded).
    """
    config = load_config()
    errors = []

    for source in config["sources"]:
        if "path" in source:
            # Local sources don't need fetching
            continue

        try:
            await fetch_remote_registry(source, force)
        except Exception as e:
            errors.append({"source": source["name"], "error": str(e)})

    return errors


async def fetch_full_bundle(source_name: str) -> None:
    """Download full bundle for a remote source."""
    config = load_config()
    source = next((s for s in config["sources"] if s["name"] == source_name), None)

    if not source or "path" in source:
        raise ValueError(f'Source "{source_name}" is not a remote source.')

    url = f"{source['url']}/bundle.tar.gz"
    tmp_path = get_source_dir(source_name) / "bundle.tar.gz"

    dir_path = get_source_dir(source_name)
    dir_path.mkdir(parents=True, exist_ok=True)

    # Download
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        tmp_path.write_bytes(response.content)

    # Extract
    data_dir = get_source_data_dir(source_name)
    data_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tmp_path, "r:gz") as tar:
        tar.extractall(path=data_dir)

    # Copy registry.json from extracted bundle if present
    extracted_registry = data_dir / "registry.json"
    if extracted_registry.exists():
        registry_path = get_source_registry_path(source_name)
        shutil.copy(extracted_registry, registry_path)

    meta = read_meta(source_name)
    meta["lastUpdated"] = int(datetime.now().timestamp() * 1000)
    meta["fullBundle"] = True
    write_meta(source_name, meta)

    tmp_path.unlink()


async def fetch_doc(source: dict[str, Any], doc_path: str) -> str:
    """Fetch a single doc. Source object must have name + (url or path).

    Args:
        source: Source dict with 'name' and either 'url' or 'path'
        doc_path: Relative path to the doc

    Returns:
        Document content as string
    """
    # Local source: read directly
    if "path" in source:
        local_path = Path(source["path"]) / doc_path
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")
        return local_path.read_text(encoding="utf-8")

    # Remote source: check cache first
    cached_path = get_source_data_dir(source["name"]) / doc_path
    if cached_path.exists():
        return cached_path.read_text(encoding="utf-8")

    # Check bundled content (shipped with package)
    bundled_path = get_bundled_dir() / doc_path
    if bundled_path.exists():
        return bundled_path.read_text(encoding="utf-8")

    # Fetch from CDN
    url = f"{source['url']}/{doc_path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        content = response.text

    # Cache locally
    cached_path.parent.mkdir(parents=True, exist_ok=True)
    cached_path.write_text(content, encoding="utf-8")

    return content


async def fetch_doc_full(
    source: dict[str, Any], base_path: str, files: list[str]
) -> list[dict[str, str]]:
    """Fetch all files in an entry directory.

    Returns:
        List of dicts with 'name' and 'content' keys
    """
    results = []
    for file in files:
        file_path = f"{base_path}/{file}"
        content = await fetch_doc(source, file_path)
        results.append({"name": file, "content": content})
    return results


def load_source_registry(source: dict[str, Any]) -> dict[str, Any] | None:
    """Load cached/local registry for a single source."""
    if "path" in source:
        # Local source: read registry.json from the folder
        reg_path = Path(source["path"]) / "registry.json"
        if not reg_path.exists():
            return None
        with open(reg_path, encoding="utf-8") as f:
            return json.load(f)

    # Remote source: read from cache
    reg_path = get_source_registry_path(source["name"])
    if not reg_path.exists():
        return None

    with open(reg_path, encoding="utf-8") as f:
        return json.load(f)


def load_search_index(source: dict[str, Any]) -> dict[str, Any] | None:
    """Load BM25 search index for a single source (if available)."""
    if "path" in source:
        base_path = Path(source["path"])
    else:
        base_path = get_source_dir(source["name"])

    index_path = base_path / "search-index.json"
    if not index_path.exists():
        return None

    try:
        with open(index_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics."""
    chub_dir = get_chub_dir()
    if not chub_dir.exists():
        return {"exists": False, "sources": []}

    config = load_config()
    source_stats = []

    for source in config["sources"]:
        if "path" in source:
            source_stats.append(
                {"name": source["name"], "type": "local", "path": source["path"]}
            )
            continue

        meta = read_meta(source["name"])
        data_dir = get_source_data_dir(source["name"])

        data_size = 0
        file_count = 0

        if data_dir.exists():
            for path in data_dir.rglob("*"):
                if path.is_file():
                    data_size += path.stat().st_size
                    file_count += 1

        last_updated = None
        if "lastUpdated" in meta:
            last_updated = (
                datetime.fromtimestamp(meta["lastUpdated"] / 1000).isoformat() + "Z"
            )

        source_stats.append(
            {
                "name": source["name"],
                "type": "remote",
                "hasRegistry": get_source_registry_path(source["name"]).exists(),
                "lastUpdated": last_updated,
                "fullBundle": meta.get("fullBundle", False),
                "fileCount": file_count,
                "dataSize": data_size,
            }
        )

    return {"exists": True, "sources": source_stats}


def clear_cache() -> None:
    """Clear the cache (preserves config.yaml)."""
    chub_dir = get_chub_dir()
    config_path = chub_dir / "config.yaml"

    config_content = None
    if config_path.exists():
        config_content = config_path.read_text(encoding="utf-8")

    if chub_dir.exists():
        shutil.rmtree(chub_dir)

    if config_content:
        chub_dir.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_content, encoding="utf-8")


async def ensure_registry() -> None:
    """Ensure at least one registry is available."""
    config = load_config()

    # Check if any source has a registry available
    has_any = False
    for source in config["sources"]:
        if "path" in source:
            reg_path = Path(source["path"]) / "registry.json"
            if reg_path.exists():
                has_any = True
                break
        else:
            if get_source_registry_path(source["name"]).exists():
                has_any = True
                break

    if has_any:
        # Auto-refresh stale remote registries (best-effort)
        for source in config["sources"]:
            if "path" in source:
                continue
            if not is_source_cache_fresh(source["name"]):
                try:
                    await fetch_remote_registry(source)
                except Exception:
                    # use stale
                    pass
        return

    # No registries at all — try bundled content first, then network
    bundled_registry = get_bundled_dir() / "registry.json"
    if bundled_registry.exists():
        # Seed cache from bundled content
        default_dir = get_source_dir("default")
        default_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(bundled_registry, get_source_registry_path("default"))
        write_meta("default", {"lastUpdated": 0, "bundledSeed": True})
        return

    # No bundled content either — must download from remote
    await fetch_all_registries(force=True)
