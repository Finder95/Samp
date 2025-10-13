from tools.autorp.slug import slugify_description


def test_slugify_description_normalises_unicode_and_separators():
    value = "Zażółć gęślą jaźń!!!"
    assert slugify_description(value) == "zazolc_gesla_jazn"


def test_slugify_description_collapses_repeated_separators():
    value = "Demo---Run___v2"
    assert slugify_description(value) == "demo-run_v2"


def test_slugify_description_enforces_length_limit():
    long_description = "X" * 120
    slug = slugify_description(long_description, max_length=32)
    assert len(slug) <= 32
    assert slug == "x" * 32


def test_slugify_description_returns_fallback_for_empty_result():
    slug = slugify_description("😊" * 4, fallback="backup")
    # Emoji are stripped entirely during ASCII normalisation so fallback is used.
    assert slug == "backup"
