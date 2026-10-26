"""Unit tests for snip.models, grouped by the SLI each test serves (docs/slis.md)."""

import pytest
from pydantic import ValidationError

from snip.models import CreateLinkRequest, LinkResponse
from snip.store import LinkRecord

# --- SLI 3: resolve correctness (the response carries the stored URL unchanged) ---


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://example.com/a?b=1&c=2#frag",
        "https://example.com/café",
    ],
)
def test_valid_url_is_accepted_unchanged(url):
    """SLI 3 / SLI 4: a validation rule must not reject or rewrite a good URL."""
    assert CreateLinkRequest(url=url).url == url


# --- SLI 4: create validation (invalid or unsafe URLs are rejected) ---


@pytest.mark.xfail(
    strict=True,
    reason="Open finding #2: CreateLinkRequest accepts any string. Remove this "
    "marker when URL validation lands; strict=True fails the run if it "
    "starts passing while the marker is still there.",
)
@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "",
        "   ",
        "not a url",
        "example.com/no-scheme",
    ],
)
def test_invalid_or_unsafe_url_is_rejected(url):
    """SLI 4."""
    with pytest.raises(ValidationError):
        CreateLinkRequest(url=url)


# --- SLI 3 / SLI 5: LinkResponse reports the stored values exactly ---


def test_link_response_carries_code_url_and_clicks_exactly():
    """SLI 3 (url) and SLI 5 (clicks) at the response boundary."""
    url = "https://example.com/Path/?q=1&r=%20#frag/"
    record = LinkRecord(code="abc123", url=url, clicks=7)

    response = LinkResponse.from_record(record)

    assert (response.code, response.url, response.clicks) == ("abc123", url, 7)
