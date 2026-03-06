import pychub.lib.registry as registry


def _reset_registry_state() -> None:
    registry._merged = None
    registry._search_index = None


def test_get_entry_ambiguous_and_namespaced(monkeypatch) -> None:
    _reset_registry_state()

    def _load_config():
        return {"sources": [{"name": "a"}, {"name": "b"}], "source": "community"}

    def _load_source_registry(source):
        if source["name"] == "a":
            return {"docs": [{"id": "openai/chat", "name": "Chat", "languages": []}]}
        if source["name"] == "b":
            return {"docs": [{"id": "openai/chat", "name": "Chat", "languages": []}]}
        return None

    monkeypatch.setattr(registry, "load_config", _load_config)
    monkeypatch.setattr(registry, "load_source_registry", _load_source_registry)
    monkeypatch.setattr(registry, "load_search_index", lambda _src: None)

    ambiguous = registry.get_entry("openai/chat")
    assert ambiguous["ambiguous"] is True
    assert len(ambiguous["alternatives"]) == 2

    resolved = registry.get_entry("a:openai/chat")
    assert resolved["ambiguous"] is False
    assert resolved["entry"]["_source"] == "a"


def test_search_entries_fallback(monkeypatch) -> None:
    _reset_registry_state()

    def _load_config():
        return {"sources": [{"name": "default"}], "source": "community"}

    def _load_source_registry(_source):
        return {
            "docs": [
                {
                    "id": "stripe/api",
                    "name": "Stripe API",
                    "description": "Payments",
                    "tags": ["payments"],
                }
            ],
            "skills": [],
        }

    monkeypatch.setattr(registry, "load_config", _load_config)
    monkeypatch.setattr(registry, "load_source_registry", _load_source_registry)
    monkeypatch.setattr(registry, "load_search_index", lambda _src: None)

    results = registry.search_entries("stripe")
    assert len(results) == 1
    assert results[0]["id"] == "stripe/api"
