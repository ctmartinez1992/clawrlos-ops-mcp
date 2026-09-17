from clawrlos_ops_mcp.scrapers.text_utils import clean_summary


def test_clean_summary_returns_none_for_empty():
    assert clean_summary(None) is None
    assert clean_summary("") is None
    assert clean_summary("   ") is None


def test_clean_summary_collapses_whitespace():
    assert clean_summary("Some\n  messy   \t text") == "Some messy text"


def test_clean_summary_truncates_long_text():
    text = "a" * 300
    result = clean_summary(text)
    assert result == "a" * 280 + "..."


def test_clean_summary_respects_custom_max_len():
    assert clean_summary("abcdef", max_len=3) == "abc..."
