from pychub.lib.frontmatter import parse_frontmatter
from pychub.lib.normalize import display_language, normalize_language


def test_parse_frontmatter_with_yaml_block() -> None:
    content = "---\nname: Stripe\nmetadata:\n  source: official\n---\nBody text"
    parsed = parse_frontmatter(content)

    assert parsed["attributes"]["name"] == "Stripe"
    assert parsed["attributes"]["metadata"]["source"] == "official"
    assert parsed["body"] == "Body text"


def test_parse_frontmatter_without_yaml_block() -> None:
    content = "Just markdown"
    parsed = parse_frontmatter(content)

    assert parsed["attributes"] == {}
    assert parsed["body"] == "Just markdown"


def test_language_normalization_and_display() -> None:
    assert normalize_language("py") == "python"
    assert normalize_language("TypeScript") == "typescript"
    assert normalize_language(None) is None
    assert display_language("python") == "py"
    assert display_language("go") == "go"
