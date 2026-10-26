"""Unit tests for snip.shortener, grouped by the SLI each test serves (docs/slis.md)."""

import string

import pytest

from snip import shortener
from snip.store import Store

# --- SLI 2: redirect availability (unknown code is a clean miss, never a crash) ---


def test_resolve_unknown_code_raises_keyerror_and_stores_nothing(fresh_store):
    """SLI 2: the miss contract the routes turn into a 404."""
    with pytest.raises(KeyError):
        shortener.resolve("nope12")

    assert fresh_store.all() == []


def test_stats_unknown_code_raises_keyerror(fresh_store):
    """SLI 2: same miss contract for the stats route."""
    with pytest.raises(KeyError):
        shortener.stats("nope12")


def test_generated_codes_are_path_safe_and_fixed_length():
    """SLI 2 / SLI 3: a code must be followable as a URL path segment."""
    safe = set(string.ascii_letters + string.digits)

    for _ in range(200):
        code = shortener.generate_code()
        assert len(code) == shortener.CODE_LENGTH
        assert set(code) <= safe


# --- SLI 3: resolve correctness (a code returns the exact stored URL) ---


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "https://example.com/a?b=1&c=%20d#frag",
        "https://example.com/café",
        "https://example.com/path/",
        "HTTP://Example.COM/MixedCase",
        "https://example.com:8443/a;b=c",
    ],
)
def test_resolve_returns_exact_url_that_was_created(fresh_store, url):
    """SLI 3: no normalisation of query, fragment, unicode, slash or case."""
    record = shortener.create_link(url)

    assert shortener.resolve(record.code).url == url
    assert shortener.stats(record.code).url == url


def test_each_code_resolves_to_its_own_url(fresh_store):
    """SLI 3: resolving one code never returns another link's URL."""
    a = shortener.create_link("https://a.example")
    b = shortener.create_link("https://b.example")

    assert shortener.resolve(a.code).url == "https://a.example"
    assert shortener.resolve(b.code).url == "https://b.example"


# --- SLI 5: stats accuracy (recorded clicks equal actual follows) ---


def test_each_follow_counts_exactly_once(fresh_store):
    """SLI 5."""
    record = shortener.create_link("https://example.com")

    for _ in range(3):
        shortener.resolve(record.code)

    assert shortener.stats(record.code).clicks == 3


def test_reading_stats_does_not_count_a_click(fresh_store):
    """SLI 5."""
    record = shortener.create_link("https://example.com")

    for _ in range(3):
        shortener.stats(record.code)

    assert shortener.stats(record.code).clicks == 0


def test_clicks_are_counted_per_link(fresh_store):
    """SLI 5."""
    a = shortener.create_link("https://a.example")
    b = shortener.create_link("https://b.example")

    shortener.resolve(a.code)
    shortener.resolve(a.code)

    assert shortener.stats(a.code).clicks == 2
    assert shortener.stats(b.code).clicks == 0


def test_following_unknown_code_changes_no_existing_count(fresh_store):
    """SLI 5: a miss must not touch any other link's counter."""
    record = shortener.create_link("https://example.com")

    with pytest.raises(KeyError):
        shortener.resolve("nope12")

    assert shortener.stats(record.code).clicks == 0
    assert len(fresh_store.all()) == 1


# --- No SLI target: capability 3 (list links) ---


def test_list_links_returns_every_created_link(fresh_store):
    """No SLI target; guards the list capability."""
    a = shortener.create_link("https://a.example")
    b = shortener.create_link("https://b.example")

    assert {r.code for r in shortener.list_links()} == {a.code, b.code}


# --- SLI 3 / SLI 5: collision must not overwrite an existing link ---



def test_colliding_code_does_not_overwrite_existing_link(monkeypatch):
    """SLI 3 / SLI 5: a code that already exists must keep its original URL."""
    monkeypatch.setattr(shortener, "store", Store())
    # Force a collision: the first two calls return the same code. A third,
    # different code is available so a fix that retries can terminate.
    codes = iter(["AAAAAA", "AAAAAA", "BBBBBB"])
    monkeypatch.setattr(shortener, "generate_code", lambda: next(codes))

    first = shortener.create_link("https://first.example")
    second = shortener.create_link("https://second.example")

    # The first link keeps its code and URL.
    assert first.code == "AAAAAA"
    assert shortener.stats(first.code).url == "https://first.example"
    # The retry must take the next generated code, and that link must resolve.
    assert second.code == "BBBBBB"
    assert shortener.stats(second.code).url == "https://second.example"
