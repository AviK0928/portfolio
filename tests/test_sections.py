import datetime as dt

from app import models

SECTION_NAMES = [
    "Projects", "Experience", "Problem solving", "Writing",
    "Skills", "Certifications", "Education",
]


def test_all_sections_present_and_empty(client):
    body = client.get("/").text
    for name in SECTION_NAMES:
        assert f">{name}<" in body, name
    assert body.count("Coming soon") == len(SECTION_NAMES)


def test_project_datasheet_renders_all_fields(client, session):
    session.add(models.Project(
        title="RedisGo", summary="Cache server",
        tech_stack=["Go", "TCP"], highlights=["RESP protocol"],
        repo_url="https://github.com/AviK0928/redisgo",
    ))
    session.commit()
    body = client.get("/").text
    for expected in ["RedisGo", "Cache server", "Go", "TCP", "RESP protocol", "Source"]:
        assert expected in body, expected


def test_current_role_shows_present(client, session):
    session.add(models.Experience(
        org="Rivigo", role="SDE Intern", kind="work",
        start_date=dt.date(2026, 1, 1), end_date=None,
    ))
    session.commit()
    body = client.get("/").text
    assert "Jan 2026 – Present" in body


def test_skills_group_by_category(client, session):
    session.add_all([
        models.Skill(category="Languages", name="Go", display_order=1),
        models.Skill(category="Languages", name="Java", display_order=2),
        models.Skill(category="Data", name="Redis", display_order=3),
    ])
    session.commit()
    body = client.get("/").text
    assert body.count("skillgroup__name") == 2


def test_dsa_missing_count_shows_dash(client, session):
    session.add(models.DsaProfile(
        platform="LeetCode", handle="AviK0928",
        profile_url="https://leetcode.com/AviK0928", problems_solved=None,
    ))
    session.commit()
    assert "—" in client.get("/").text


def test_socials_render_in_footer(client, session):
    session.add(models.SocialLink(platform="GitHub", url="https://github.com/AviK0928"))
    session.commit()
    body = client.get("/").text
    assert "GitHub" in body and "socials" in body
