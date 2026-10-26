import pytest

from snip import shortener
from snip.store import Store


@pytest.fixture
def fresh_store(monkeypatch):
    """Give shortener an empty store so tests never share links or click counts."""
    s = Store()
    monkeypatch.setattr(shortener, "store", s)
    return s
