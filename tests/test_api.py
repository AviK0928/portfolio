import datetime as dt

from app import models

SECTIONS = [
    "social-links", "projects", "experience", "dsa-profiles",
    "blogs", "skills", "certifications", "education",
]


def test_all_sections_respond_empty_on_fresh_db(client):
    for name in SECTIONS:
        r = client.get(f"/api/v1/sections/{name}")
        assert r.status_code == 200, name
        assert r.json() == {"state": "empty", "items": []}, name


def test_unknown_section_is_404(client):
    assert client.get("/api/v1/sections/nonsense").status_code == 404


def test_project_payload_excludes_internal_fields(client, session):
    session.add(models.Project(
        title="Invoice Generator", summary="microservices",
        tech_stack=["Java", "Kafka"], display_order=3, is_published=True,
    ))
    session.commit()

    body = client.get("/api/v1/sections/projects").json()
    assert body["state"] == "ready"
    item = body["items"][0]
    assert item["title"] == "Invoice Generator"
    assert item["tech_stack"] == ["Java", "Kafka"]
    for leaked in ("id", "display_order", "is_published", "created_at", "updated_at"):
        assert leaked not in item


def test_cache_headers_present(client):
    r = client.get("/api/v1/sections/blogs")
    cc = r.headers["cache-control"]
    assert "s-maxage=300" in cc
    assert "stale-while-revalidate=86400" in cc


def test_profile_absent_reports_empty(client):
    assert client.get("/api/v1/profile").json() == {"state": "empty", "item": None}


def test_profile_present_reports_ready(client, session):
    session.add(models.SiteProfile(
        id=1, name="Aviraj Khanchi", headline="Software Engineer",
        email="a@example.com",
    ))
    session.commit()
    body = client.get("/api/v1/profile").json()
    assert body["state"] == "ready"
    assert body["item"]["name"] == "Aviraj Khanchi"
    assert "id" not in body["item"]


def test_experience_dates_serialise(client, session):
    session.add(models.Experience(
        org="Rivigo", role="SDE Intern", kind="work",
        start_date=dt.date(2026, 1, 1), end_date=dt.date(2026, 7, 1),
        bullets=["shipped X"],
    ))
    session.commit()
    item = client.get("/api/v1/sections/experience").json()["items"][0]
    assert item["start_date"] == "2026-01-01"
    assert item["bullets"] == ["shipped X"]
