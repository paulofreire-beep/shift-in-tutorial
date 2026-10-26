"""Unit tests for snip.shortener."""

from snip import shortener
from snip.store import Store


def test_colliding_code_does_not_overwrite_existing_link(monkeypatch):
    """SLI 3 / SLI 5: a code that already exists must keep its original URL."""
    monkeypatch.setattr(shortener, "store", Store())
    # Force a collision: the first two calls return the same code. A third,
    # different code is available so a fix that retries can terminate.
    codes = iter(["AAAAAA", "AAAAAA", "BBBBBB"])
    monkeypatch.setattr(shortener, "generate_code", lambda: next(codes))

    first = shortener.create_link("https://first.example")
    shortener.create_link("https://second.example")

    assert shortener.stats(first.code).url == "https://first.example"
