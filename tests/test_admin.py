import pytest

from app.config import get_settings
from app.main import app

TOKEN = "test-token-value"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture()
def admin_client(client, monkeypatch):
    """Override the settings dependency so the configured token is known."""
    from app import security

    settings = get_settings().model_copy(update={"admin_api_token": TOKEN})
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    yield client
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture()
def unconfigured_client(client):
    settings = get_settings().model_copy(update={"admin_api_token": ""})
    app.dependency_overrides[get_settings] = lambda: settings
    yield client
    app.dependency_overrides.pop(get_settings, None)


# ---------------- auth ----------------

def test_missing_token_is_401(admin_client):
    assert admin_client.get("/api/v1/admin/projects").status_code == 401


def test_wrong_token_is_401(admin_client):
    r = admin_client.get("/api/v1/admin/projects",
                         headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_wrong_scheme_is_401(admin_client):
    r = admin_client.get("/api/v1/admin/projects",
                         headers={"Authorization": f"Basic {TOKEN}"})
    assert r.status_code == 401


def test_empty_bearer_is_401(admin_client):
    r = admin_client.get("/api/v1/admin/projects",
                         headers={"Authorization": "Bearer "})
    assert r.status_code == 401


def test_unconfigured_token_locks_api_shut(unconfigured_client):
    """An unset token must lock the API, never open it."""
    for headers in ({}, {"Authorization": "Bearer "}, {"Authorization": "Bearer x"}):
        r = unconfigured_client.get("/api/v1/admin/projects", headers=headers)
        assert r.status_code == 503, headers


def test_valid_token_is_accepted(admin_client):
    r = admin_client.get("/api/v1/admin/projects", headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {"items": []}


# ---------------- CRUD ----------------

def test_create_read_update_delete_project(admin_client):
    created = admin_client.post("/api/v1/admin/projects", headers=AUTH, json={
        "title": "RedisGo", "summary": "Cache server",
        "tech_stack": ["Go"], "display_order": 1,
    })
    assert created.status_code == 201
    row_id = created.json()["id"]
    assert created.json()["title"] == "RedisGo"

    listed = admin_client.get("/api/v1/admin/projects", headers=AUTH).json()
    assert len(listed["items"]) == 1

    updated = admin_client.put(f"/api/v1/admin/projects/{row_id}", headers=AUTH, json={
        "title": "RedisGo", "summary": "Redis-compatible cache server",
        "tech_stack": ["Go", "TCP"], "display_order": 1,
    })
    assert updated.status_code == 200
    assert updated.json()["tech_stack"] == ["Go", "TCP"]

    assert admin_client.delete(f"/api/v1/admin/projects/{row_id}",
                               headers=AUTH).status_code == 204
    assert admin_client.get("/api/v1/admin/projects", headers=AUTH).json() == {"items": []}


def test_unpublished_row_hidden_from_public_api(admin_client):
    admin_client.post("/api/v1/admin/blogs", headers=AUTH, json={
        "title": "Draft", "url": "https://example.com", "is_published": False,
    })
    assert admin_client.get("/api/v1/admin/blogs", headers=AUTH).json()["items"]
    assert admin_client.get("/api/v1/sections/blogs").json()["state"] == "empty"


def test_display_order_controls_public_ordering(admin_client):
    for name, order in [("Go", 2), ("Java", 1)]:
        admin_client.post("/api/v1/admin/skills", headers=AUTH,
                          json={"category": "Languages", "name": name,
                                "display_order": order})
    items = admin_client.get("/api/v1/sections/skills").json()["items"]
    assert [i["name"] for i in items] == ["Java", "Go"]


def test_unknown_field_is_rejected(admin_client):
    r = admin_client.post("/api/v1/admin/projects", headers=AUTH, json={
        "title": "X", "summary": "Y", "titel": "typo",
    })
    assert r.status_code == 422


def test_missing_required_field_is_422(admin_client):
    r = admin_client.post("/api/v1/admin/projects", headers=AUTH, json={"title": "X"})
    assert r.status_code == 422


def test_unknown_resource_is_404(admin_client):
    assert admin_client.get("/api/v1/admin/nonsense", headers=AUTH).status_code == 404


def test_update_missing_row_is_404(admin_client):
    r = admin_client.put("/api/v1/admin/projects/999", headers=AUTH,
                         json={"title": "X", "summary": "Y"})
    assert r.status_code == 404


def test_profile_upsert_creates_then_replaces(admin_client):
    first = admin_client.put("/api/v1/admin/profile", headers=AUTH, json={
        "name": "Aviraj Khanchi", "headline": "Backend Engineer",
    })
    assert first.status_code == 200

    second = admin_client.put("/api/v1/admin/profile", headers=AUTH, json={
        "name": "Aviraj Khanchi", "headline": "Software Engineer",
        "email": "a@example.com",
    })
    assert second.json()["headline"] == "Software Engineer"

    public = admin_client.get("/api/v1/profile").json()
    assert public["item"]["headline"] == "Software Engineer"


def test_admin_responses_are_not_cached(admin_client):
    r = admin_client.get("/api/v1/admin/projects", headers=AUTH)
    assert "s-maxage" not in r.headers.get("cache-control", "")


def test_validation_error_names_the_bad_field(admin_client):
    """422 must identify the field; a 500 would only say 'Internal Server Error'."""
    r = admin_client.post("/api/v1/admin/projects", headers=AUTH, json={
        "title": "X", "summary": "Y", "titel": "typo",
    })
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert any("titel" in str(err.get("loc", "")) for err in detail)
    assert not any("errors.pydantic.dev" in str(err) for err in detail)
