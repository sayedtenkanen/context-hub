"""BM25 search implementation for Context Hub.

Port of cli/src/lib/bm25.js
"""

import math
import re
from typing import Any

# Default BM25 parameters
DEFAULT_K1 = 1.5
DEFAULT_B = 0.75

# Field weights for multi-field scoring
FIELD_WEIGHTS = {
    "name": 3.0,
    "tags": 2.0,
    "description": 1.0,
}

# Common stop words to filter out
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
    "this",
    "but",
    "not",
    "you",
    "your",
    "can",
    "do",
    "does",
    "how",
    "if",
    "may",
    "no",
    "so",
    "than",
    "too",
    "very",
    "just",
    "about",
    "into",
    "over",
    "such",
    "then",
    "them",
    "these",
    "those",
    "through",
    "under",
    "use",
    "using",
    "used",
}


def tokenize(text: str | None) -> list[str]:
    """Tokenize text into lowercase terms with stop word removal.

    Must be used identically at build time and search time.
    """
    if not text:
        return []

    # Normalize and split
    normalized = re.sub(r"[^a-z0-9\s-]", " ", text.lower())
    tokens = re.split(r"[\s-]+", normalized)

    # Filter: length > 1 and not a stop word
    return [t for t in tokens if len(t) > 1 and t not in STOP_WORDS]


def build_index(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a BM25 search index from registry entries.

    Called during build time.

    Args:
        entries: Combined docs and skills from registry

    Returns:
        The search index dictionary
    """
    documents = []
    df_map: dict[str, int] = {}  # document frequency per term
    field_lengths: dict[str, list[int]] = {"name": [], "description": [], "tags": []}

    for entry in entries:
        name_tokens = tokenize(entry.get("name", ""))
        desc_tokens = tokenize(entry.get("description", ""))
        tag_tokens = []
        for tag in entry.get("tags", []):
            tag_tokens.extend(tokenize(tag))

        documents.append(
            {
                "id": entry["id"],
                "tokens": {
                    "name": name_tokens,
                    "description": desc_tokens,
                    "tags": tag_tokens,
                },
            }
        )

        field_lengths["name"].append(len(name_tokens))
        field_lengths["description"].append(len(desc_tokens))
        field_lengths["tags"].append(len(tag_tokens))

        # Count document frequency — a term counts once per document
        all_terms = set(name_tokens + desc_tokens + tag_tokens)
        for term in all_terms:
            df_map[term] = df_map.get(term, 0) + 1

    n = len(documents)

    # Compute IDF for each term
    idf: dict[str, float] = {}
    for term, df in df_map.items():
        idf[term] = math.log((n - df + 0.5) / (df + 0.5) + 1)

    # Compute average field lengths
    def avg(arr: list[int]) -> float:
        return sum(arr) / len(arr) if arr else 0.0

    avg_field_lengths = {
        "name": avg(field_lengths["name"]),
        "description": avg(field_lengths["description"]),
        "tags": avg(field_lengths["tags"]),
    }

    return {
        "version": "1.0.0",
        "algorithm": "bm25",
        "params": {"k1": DEFAULT_K1, "b": DEFAULT_B},
        "totalDocs": n,
        "avgFieldLengths": avg_field_lengths,
        "idf": idf,
        "documents": documents,
    }


def score_field(
    query_terms: list[str],
    field_tokens: list[str],
    idf: dict[str, float],
    avg_field_len: float,
    k1: float,
    b: float,
) -> float:
    """Compute BM25 score for a single field."""
    if not field_tokens:
        return 0.0

    # Build term frequency map for this field
    tf: dict[str, int] = {}
    for t in field_tokens:
        tf[t] = tf.get(t, 0) + 1

    score = 0.0
    dl = len(field_tokens)

    for term in query_terms:
        term_freq = tf.get(term, 0)
        if term_freq == 0:
            continue

        term_idf = idf.get(term, 0.0)
        numerator = term_freq * (k1 + 1)
        denominator = term_freq + k1 * (1 - b + b * (dl / (avg_field_len or 1)))
        score += term_idf * (numerator / denominator)

    return score


def search(
    query: str, index: dict[str, Any], opts: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Search the BM25 index with a query string.

    Args:
        query: The search query
        index: The pre-built BM25 index
        opts: Options dict with optional 'limit' key

    Returns:
        Sorted results: [{"id": ..., "score": ...}, ...]
    """
    query_terms = tokenize(query)
    if not query_terms:
        return []

    k1 = index["params"]["k1"]
    b = index["params"]["b"]
    results = []

    for doc in index["documents"]:
        total_score = 0.0

        for field, weight in FIELD_WEIGHTS.items():
            field_tokens = doc["tokens"].get(field, [])
            avg_len = index["avgFieldLengths"].get(field, 1.0)
            field_score = score_field(
                query_terms, field_tokens, index["idf"], avg_len, k1, b
            )
            total_score += field_score * weight

        if total_score > 0:
            results.append({"id": doc["id"], "score": total_score})

    results.sort(key=lambda x: x["score"], reverse=True)

    if opts and "limit" in opts:
        return results[: opts["limit"]]

    return results
