from app.text.clean import clean, collapse_whitespace, dehyphenate, strip_page_numbers


def test_dehyphenate_joins_line_wrapped_words():
    assert dehyphenate("exam-\nple") == "example"
    assert dehyphenate("docu-\n  ment") == "document"


def test_dehyphenate_leaves_normal_hyphens():
    assert dehyphenate("well-known") == "well-known"


def test_strip_page_numbers():
    text = "First line\n42\nSecond line\nPage 7\n"
    assert strip_page_numbers(text) == "First line\nSecond line"


def test_collapse_whitespace():
    assert collapse_whitespace("  a\n\n b   c \t d ") == "a b c d"


def test_clean_full_pass():
    raw = "The quick brown fox jum-\nped over\n12\nthe lazy dog.\n"
    assert clean(raw) == "The quick brown fox jumped over the lazy dog."
