from pychub.lib.bm25 import build_index, search, tokenize


def test_tokenize_filters_stopwords_and_normalizes() -> None:
    tokens = tokenize("The Stripe API - webhook events and retries!")
    assert "the" not in tokens
    assert "stripe" in tokens
    assert "webhook" in tokens
    assert "retries" in tokens


def test_bm25_search_returns_relevant_results() -> None:
    entries = [
        {
            "id": "stripe/api",
            "name": "Stripe API",
            "description": "Payments and webhooks guide",
            "tags": ["payments", "webhook"],
        },
        {
            "id": "openai/chat",
            "name": "OpenAI Chat",
            "description": "Chat completions API",
            "tags": ["ai", "llm"],
        },
    ]

    index = build_index(entries)
    results = search("stripe webhook", index)

    assert len(results) >= 1
    assert results[0]["id"] == "stripe/api"
    assert results[0]["score"] > 0
