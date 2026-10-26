import pytest
from fastapi.testclient import TestClient

from snip import shortener
from snip.main import app
from snip.store import Store


@pytest.fixture
def client(monkeypatch):
    """TestClient over the real app with an empty store, so tests never share links."""
    monkeypatch.setattr(shortener, "store", Store())
    return TestClient(app)
