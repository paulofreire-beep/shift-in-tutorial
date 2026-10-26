"""Unit tests for snip.store, grouped by the SLI each test serves (docs/slis.md)."""

import pytest

from snip.store import LinkRecord, Store


def test_get_unknown_code_raises_keyerror():
    """SLI 2: the miss contract shortener and the routes rely on."""
    with pytest.raises(KeyError):
        Store().get("nope12")


def test_get_returns_the_exact_url_that_was_put():
    """SLI 3."""
    s = Store()
    s.put(LinkRecord(code="abc123", url="https://example.com/a?b=1#c"))

    assert s.get("abc123").url == "https://example.com/a?b=1#c"


def test_codes_are_stored_independently():
    """SLI 3."""
    s = Store()
    s.put(LinkRecord(code="aaaaaa", url="https://a.example"))
    s.put(LinkRecord(code="bbbbbb", url="https://b.example"))

    assert s.get("aaaaaa").url == "https://a.example"
    assert s.get("bbbbbb").url == "https://b.example"


def test_new_record_starts_with_zero_clicks():
    """SLI 5: the counter must start at zero or every count is off."""
    assert LinkRecord(code="abc123", url="https://example.com").clicks == 0


def test_get_returns_the_live_record_so_a_click_is_remembered():
    """SLI 5: a count added to the fetched record is what the next read sees."""
    s = Store()
    s.put(LinkRecord(code="abc123", url="https://example.com"))

    s.get("abc123").clicks += 1

    assert s.get("abc123").clicks == 1


def test_exists_reflects_what_was_put():
    """SLI 3 / SLI 5: shortener's collision check depends on this."""
    s = Store()
    s.put(LinkRecord(code="abc123", url="https://example.com"))

    assert s.exists("abc123") is True
    assert s.exists("zzzzzz") is False


def test_all_returns_every_record():
    """No SLI target; guards the list capability."""
    s = Store()
    s.put(LinkRecord(code="aaaaaa", url="https://a.example"))
    s.put(LinkRecord(code="bbbbbb", url="https://b.example"))

    assert {r.code for r in s.all()} == {"aaaaaa", "bbbbbb"}
