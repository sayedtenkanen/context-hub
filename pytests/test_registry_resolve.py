from pychub.lib.registry import resolve_doc_path, resolve_entry_file


def test_resolve_doc_path_for_skill() -> None:
    entry = {
        "id": "pw-community/login-flows",
        "path": "playwright-community/skills/login-flows",
        "files": ["SKILL.md"],
        "_sourceObj": {"name": "default", "url": "https://example.com"},
    }

    resolved = resolve_doc_path(entry, language=None, version=None)
    assert resolved is not None
    assert resolved["path"] == "playwright-community/skills/login-flows"

    file_info = resolve_entry_file(resolved, "skill")
    assert file_info["filePath"].endswith("/SKILL.md")


def test_resolve_doc_path_requires_language_when_multiple() -> None:
    entry = {
        "id": "openai/chat",
        "languages": [
            {
                "language": "python",
                "recommendedVersion": "1.0.0",
                "versions": [
                    {
                        "version": "1.0.0",
                        "path": "openai/docs/chat",
                        "files": ["DOC.md"],
                    }
                ],
            },
            {
                "language": "javascript",
                "recommendedVersion": "1.0.0",
                "versions": [
                    {
                        "version": "1.0.0",
                        "path": "openai/docs/chat-js",
                        "files": ["DOC.md"],
                    }
                ],
            },
        ],
        "_sourceObj": {"name": "default", "url": "https://example.com"},
    }

    resolved = resolve_doc_path(entry, language=None, version=None)
    assert resolved is not None
    assert resolved.get("needsLanguage") is True
    assert set(resolved.get("available", [])) == {"python", "javascript"}
