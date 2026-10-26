"""API tests for the four routes: status code and response structure only.

Input-validation cases live in tests/unit/test_models.py. Value-level checks
(exact URL, click counts) are deliberately not asserted here.
"""

LINK_KEYS = {"code", "url", "clicks"}


def _assert_link_shape(body):
    assert set(body) == LINK_KEYS
    assert isinstance(body["code"], str)
    assert isinstance(body["url"], str)
    assert isinstance(body["clicks"], int)


def _create(client, url="https://example.com"):
    return client.post("/api/links", json={"url": url}).json()["code"]


# POST /api/links


def test_create_link_returns_201_and_link_shape(client):
    response = client.post("/api/links", json={"url": "https://example.com"})

    assert response.status_code == 201
    _assert_link_shape(response.json())


# GET /api/links


def test_list_links_empty_returns_200_and_empty_list(client):
    response = client.get("/api/links")

    assert response.status_code == 200
    assert response.json() == []


def test_list_links_returns_200_and_a_list_of_link_shapes(client):
    _create(client)

    response = client.get("/api/links")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list) and len(body) == 1
    _assert_link_shape(body[0])


# GET /api/links/{code}/stats


def test_stats_known_code_returns_200_and_link_shape(client):
    code = _create(client)

    response = client.get(f"/api/links/{code}/stats")

    assert response.status_code == 200
    _assert_link_shape(response.json())


def test_stats_unknown_code_returns_404_with_detail(client):
    response = client.get("/api/links/nope12/stats")

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


# GET /{code}


def test_follow_known_code_returns_307_with_location_header(client):
    code = _create(client)

    response = client.get(f"/{code}", follow_redirects=False)

    assert response.status_code == 307
    assert "location" in response.headers


def test_follow_unknown_code_returns_404_with_detail(client):
    response = client.get("/nope12", follow_redirects=False)

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)
