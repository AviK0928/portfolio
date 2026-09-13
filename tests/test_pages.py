import re

from app import models


def section_html(body: str, section_id: str) -> str:
    """Isolate one section. Page-wide assertions break as sections are added."""
    match = re.search(
        rf'<section class="section" id="{section_id}">(.*?)</section>',
        body, re.DOTALL,
    )
    assert match, f"section {section_id!r} not found"
    return match.group(1)


def test_index_renders_with_empty_db(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Coming soon" in r.text
    assert "Nothing published here yet." in r.text


def test_index_sets_cache_headers(client):
    cc = client.get("/").headers["cache-control"]
    assert "s-maxage=300" in cc and "stale-while-revalidate=86400" in cc


def test_index_uses_profile_when_present(client, session):
    session.add(models.SiteProfile(
        id=1, name="Aviraj Khanchi", headline="Backend Engineer",
        location="Rohtak, India", email="a@example.com", bio="Systems and backends.",
    ))
    session.commit()
    body = client.get("/").text
    assert "Aviraj Khanchi" in body
    assert "Rohtak, India" in body
    assert "Systems and backends." in body


def test_index_survives_missing_profile(client):
    assert "Portfolio" in client.get("/").text


def test_stylesheet_is_linked(client):
    assert '/styles.css' in client.get("/").text


def test_ready_section_renders_content_not_placeholder(client, session):
    session.add(models.Project(title="RedisGo", summary="Redis-compatible cache"))
    session.commit()
    projects = section_html(client.get("/").text, "projects")
    assert "RedisGo" in projects
    assert "Coming soon" not in projects
    assert "Nothing published here yet." not in projects


def test_unavailable_section_does_not_claim_empty(client, monkeypatch):
    """A failed query must never render as 'Coming soon'."""
    from app import repository

    def boom(_session):
        return repository.Section(repository.SectionState.UNAVAILABLE, ())

    monkeypatch.setattr("app.pages.repo.get_projects", boom)
    projects = section_html(client.get("/").text, "projects")
    assert "Temporarily unavailable" in projects
    assert "Coming soon" not in projects
    assert "Nothing published here yet." not in projects
