"""Registry management and entry resolution.

Port of cli/src/lib/registry.js
"""

from typing import Any

from . import bm25
from .cache import load_search_index, load_source_registry
from .config import load_config
from .normalize import normalize_language

_merged: dict[str, Any] | None = None
_search_index: dict[str, Any] | None = None


def get_merged() -> dict[str, list[dict[str, Any]]]:
    """Load and merge entries from all configured sources.

    Returns:
        Dict with 'docs' and 'skills' lists, entries tagged with _source/_sourceObj
    """
    global _merged, _search_index

    if _merged is not None:
        return _merged

    config = load_config()
    all_docs = []
    all_skills = []
    search_indexes = []

    for source in config["sources"]:
        registry = load_source_registry(source)
        if not registry:
            continue

        # Load BM25 search index if available
        idx = load_search_index(source)
        if idx:
            search_indexes.append(idx)

        # Support both new format (docs/skills) and old format (entries)
        if "docs" in registry:
            for doc in registry["docs"]:
                all_docs.append(
                    {
                        **doc,
                        "id": doc.get("id") or doc["name"],
                        "_source": source["name"],
                        "_sourceObj": source,
                    }
                )

        if "skills" in registry:
            for skill in registry["skills"]:
                all_skills.append(
                    {
                        **skill,
                        "id": skill.get("id") or skill["name"],
                        "_source": source["name"],
                        "_sourceObj": source,
                    }
                )

        # Backward compat: old entries[] format
        if "entries" in registry:
            for entry in registry["entries"]:
                tagged = {**entry, "_source": source["name"], "_sourceObj": source}
                provides = (
                    entry.get("languages", [{}])[0]
                    .get("versions", [{}])[0]
                    .get("provides", [])
                )
                if "skill" in provides:
                    all_skills.append(tagged)
                if "doc" in provides or not provides:
                    all_docs.append(tagged)

    # Merge search indexes if multiple exist
    if search_indexes:
        if len(search_indexes) == 1:
            _search_index = search_indexes[0]
        else:
            # Merge: combine documents, recompute global IDF
            all_documents = []
            for idx in search_indexes:
                all_documents.extend(idx["documents"])

            n = len(all_documents)
            df_map: dict[str, int] = {}
            field_lengths: dict[str, list[int]] = {
                "name": [],
                "description": [],
                "tags": [],
            }

            for doc in all_documents:
                all_terms = set()
                for field in ["name", "description", "tags"]:
                    tokens = doc["tokens"].get(field, [])
                    all_terms.update(tokens)
                    field_lengths[field].append(len(tokens))

                for term in all_terms:
                    df_map[term] = df_map.get(term, 0) + 1

            idf = {}
            for term, df in df_map.items():
                import math

                idf[term] = math.log((n - df + 0.5) / (df + 0.5) + 1)

            def avg(arr: list[int]) -> float:
                return sum(arr) / len(arr) if arr else 0.0

            _search_index = {
                "version": "1.0.0",
                "algorithm": "bm25",
                "params": search_indexes[0]["params"],
                "totalDocs": n,
                "avgFieldLengths": {
                    "name": avg(field_lengths["name"]),
                    "description": avg(field_lengths["description"]),
                    "tags": avg(field_lengths["tags"]),
                },
                "idf": idf,
                "documents": all_documents,
            }

    _merged = {"docs": all_docs, "skills": all_skills}
    return _merged


def get_all_entries() -> list[dict[str, Any]]:
    """Get all entries (docs + skills combined) for listing/searching."""
    merged = get_merged()
    tagged_docs = [{**d, "_type": "doc"} for d in merged["docs"]]
    tagged_skills = [{**s, "_type": "skill"} for s in merged["skills"]]
    return tagged_docs + tagged_skills


def apply_source_filter(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter entries by the global source trust policy."""
    config = load_config()
    allowed = [s.strip().lower() for s in config["source"].split(",")]
    return [e for e in entries if not e.get("source") or e["source"].lower() in allowed]


def apply_filters(
    entries: list[dict[str, Any]], filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """Apply tag and language filters."""
    result = entries

    if "tags" in filters and filters["tags"]:
        filter_tags = [t.strip().lower() for t in filters["tags"].split(",")]
        result = [
            e
            for e in result
            if all(
                any(t.lower() == ft for t in e.get("tags", [])) for ft in filter_tags
            )
        ]

    if "lang" in filters and filters["lang"]:
        lang = normalize_language(filters["lang"])
        result = [
            e
            for e in result
            if any(l["language"] == lang for l in e.get("languages", []))
        ]

    return result


def is_multi_source() -> bool:
    """Check if we're in multi-source mode."""
    config = load_config()
    return len(config["sources"]) > 1


def get_display_id(entry: dict[str, Any]) -> str:
    """Get the display id for an entry — namespaced only on collision."""
    if not is_multi_source():
        return entry["id"]

    all_entries = apply_source_filter(get_all_entries())
    matches = [
        e
        for e in all_entries
        if e["id"] == entry["id"] and e.get("_type") == entry.get("_type")
    ]

    if len(matches) > 1:
        return f"{entry['_source']}:{entry['id']}"

    return entry["id"]


def search_entries(
    query: str, filters: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Search entries by query string. Searches both docs and skills.

    Uses BM25 when a search index is available, falls back to keyword matching.
    """
    if filters is None:
        filters = {}

    entries = apply_source_filter(get_all_entries())

    # Deduplicate: same id+source appearing as both doc and skill → show once
    seen = set()
    deduped = []
    for entry in entries:
        key = f"{entry['_source']}:{entry['id']}"
        if key not in seen:
            seen.add(key)
            deduped.append(entry)

    # Build entry lookup by id
    entry_by_id = {entry["id"]: entry for entry in deduped}

    results = []

    if _search_index:
        # BM25 search
        bm25_results = bm25.search(query, _search_index)
        for r in bm25_results:
            entry = entry_by_id.get(r["id"])
            if entry:
                results.append({"entry": entry, "score": r["score"]})
    else:
        # Fallback: keyword matching
        q = query.lower()
        words = q.split()

        for entry in deduped:
            score = 0

            if entry["id"] == q:
                score += 100
            elif q in entry["id"]:
                score += 50

            name_lower = entry["name"].lower()
            if name_lower == q:
                score += 80
            elif q in name_lower:
                score += 40

            for word in words:
                if word in entry["id"]:
                    score += 10
                if word in name_lower:
                    score += 10
                if word in entry.get("description", "").lower():
                    score += 5
                if any(word in t.lower() for t in entry.get("tags", [])):
                    score += 15

            if score > 0:
                results.append({"entry": entry, "score": score})

    # Filter
    filtered = apply_filters([r["entry"] for r in results], filters)
    filtered_set = set(id(e) for e in filtered)
    results = [r for r in results if id(r["entry"]) in filtered_set]

    results.sort(key=lambda r: r["score"], reverse=True)
    return [{**r["entry"], "_score": r["score"]} for r in results]


def get_entry(
    id_or_namespaced_id: str, type_filter: str | None = None
) -> dict[str, Any]:
    """Get entry by id or source:id.

    Args:
        id_or_namespaced_id: Entry ID or source:id format
        type_filter: "doc", "skill", or None to search both

    Returns:
        Dict with 'entry' (or None), 'ambiguous' (bool), and 'alternatives' (list)
    """
    merged = get_merged()

    if type_filter == "doc":
        pool = apply_source_filter(merged["docs"])
    elif type_filter == "skill":
        pool = apply_source_filter(merged["skills"])
    else:
        pool = apply_source_filter(merged["docs"] + merged["skills"])

    # Check for source:id format
    if ":" in id_or_namespaced_id:
        colon_idx = id_or_namespaced_id.index(":")
        source_name = id_or_namespaced_id[:colon_idx]
        entry_id = id_or_namespaced_id[colon_idx + 1 :]
        entry = next(
            (e for e in pool if e["_source"] == source_name and e["id"] == entry_id),
            None,
        )
        return {"entry": entry, "ambiguous": False, "alternatives": []}

    # Bare id
    matches = [e for e in pool if e["id"] == id_or_namespaced_id]

    if not matches:
        return {"entry": None, "ambiguous": False, "alternatives": []}

    if len(matches) == 1:
        return {"entry": matches[0], "ambiguous": False, "alternatives": []}

    # Ambiguous
    return {
        "entry": None,
        "ambiguous": True,
        "alternatives": [f"{e['_source']}:{e['id']}" for e in matches],
    }


def list_entries(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """List entries with optional filters. Searches both docs and skills, deduped."""
    if filters is None:
        filters = {}

    entries = apply_source_filter(get_all_entries())

    # Deduplicate
    seen = set()
    deduped = []
    for entry in entries:
        key = f"{entry['_source']}:{entry['id']}"
        if key not in seen:
            seen.add(key)
            deduped.append(entry)

    return apply_filters(deduped, filters)


def resolve_doc_path(
    entry: dict[str, Any], language: str | None, version: str | None
) -> dict[str, Any] | None:
    """Resolve the doc path + source for a doc entry.

    Returns dict with 'source', 'path', 'files', or error indicators.
    """
    lang = normalize_language(language) if language else None

    # Skills are flat — no language/version nesting
    if "languages" not in entry:
        if "path" not in entry:
            return None
        return {
            "source": entry["_sourceObj"],
            "path": entry["path"],
            "files": entry.get("files", []),
        }

    lang_obj = None
    if lang:
        lang_obj = next((l for l in entry["languages"] if l["language"] == lang), None)
    elif len(entry["languages"]) == 1:
        lang_obj = entry["languages"][0]
    elif len(entry["languages"]) > 1:
        return {
            "needsLanguage": True,
            "available": [l["language"] for l in entry["languages"]],
        }

    if not lang_obj:
        return None

    ver_obj = None
    if version:
        ver_obj = next(
            (v for v in lang_obj.get("versions", []) if v["version"] == version), None
        )
        if not ver_obj:
            return {
                "versionNotFound": True,
                "requested": version,
                "available": [v["version"] for v in lang_obj.get("versions", [])],
            }
    else:
        rec = lang_obj.get("recommendedVersion")
        ver_obj = next(
            (v for v in lang_obj.get("versions", []) if v["version"] == rec),
            lang_obj.get("versions", [None])[0] if lang_obj.get("versions") else None,
        )

    if not ver_obj or "path" not in ver_obj:
        return None

    return {
        "source": entry["_sourceObj"],
        "path": ver_obj["path"],
        "files": ver_obj.get("files", []),
    }


def resolve_entry_file(
    resolved: dict[str, Any] | None, entry_type: str
) -> dict[str, Any]:
    """Given a resolved path and a type, return the entry file path."""
    if not resolved or resolved.get("needsLanguage") or resolved.get("versionNotFound"):
        return {"error": "unresolved"}

    file_name = "SKILL.md" if entry_type == "skill" else "DOC.md"

    return {
        "filePath": f"{resolved['path']}/{file_name}",
        "basePath": resolved["path"],
        "files": resolved.get("files", []),
    }
