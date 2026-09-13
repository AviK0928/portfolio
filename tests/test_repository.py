import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import models, repository as repo
from app.repository import SectionState


def test_empty_table_reports_empty_not_ready(session):
    section = repo.get_projects(session)
    assert section.state is SectionState.EMPTY
    assert section.items == ()


def test_populated_table_reports_ready(session):
    session.add(models.Project(title="RedisGo", summary="cache server"))
    session.commit()
    section = repo.get_projects(session)
    assert section.state is SectionState.READY
    assert len(section.items) == 1


def test_unpublished_rows_are_excluded(session):
    session.add(models.Blog(title="draft", url="https://x", is_published=False))
    session.commit()
    assert repo.get_blogs(session).state is SectionState.EMPTY


def test_display_order_is_respected(session):
    session.add_all([
        models.Skill(category="lang", name="Go", display_order=2),
        models.Skill(category="lang", name="Java", display_order=1),
    ])
    session.commit()
    assert [s.name for s in repo.get_skills(session).items] == ["Java", "Go"]


def test_db_failure_reports_unavailable_not_empty(session, monkeypatch):
    """The contract that matters: a broken query must never look like no content."""
    def boom(*_a, **_kw):
        raise SQLAlchemyError("connection lost")

    monkeypatch.setattr(session, "execute", boom)
    section = repo.get_dsa_profiles(session)
    assert section.state is SectionState.UNAVAILABLE
    assert section.items == ()


@pytest.mark.parametrize("fetch", [
    repo.get_social_links, repo.get_projects, repo.get_experience,
    repo.get_dsa_profiles, repo.get_blogs, repo.get_skills,
    repo.get_certifications, repo.get_education,
])
def test_every_section_queries_cleanly(session, fetch):
    assert fetch(session).state is SectionState.EMPTY
