"""Server-rendered pages. Assembles every section in one request."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import repository as repo
from app.config import get_settings
from app.db import get_session

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


def _month_year(value) -> str:
    """Dates render as 'Jan 2026'; a missing end date means the role is current."""
    return value.strftime("%b %Y") if value else "Present"


templates.env.filters["monthyear"] = _month_year

_settings = get_settings()

DEFAULT_STATEMENT = [
    "I build backend systems:",
    "caches, message pipelines,",
    "and query engines.",
]

_CACHE_CONTROL = (
    f"public, s-maxage={_settings.public_cache_seconds}, "
    f"stale-while-revalidate=86400"
)


@router.get("/")
def index(request: Request, session: Session = Depends(get_session)):
    profile = repo.get_profile(session)

    context = {
        "profile": profile,
        "statement_lines": DEFAULT_STATEMENT,
        "page_title": f"{profile.name} — {profile.headline}" if profile else "Portfolio",
        "page_description": profile.headline if profile else "",
        "projects": repo.get_projects(session),
        "experience": repo.get_experience(session),
        "dsa": repo.get_dsa_profiles(session),
        "blogs": repo.get_blogs(session),
        "skills": repo.get_skills(session),
        "skill_order": ["Languages", "Backend", "Data", "Infra"],
        "certifications": repo.get_certifications(session),
        "education": repo.get_education(session),
        "socials": repo.get_social_links(session),
    }

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=context,
        headers={"Cache-Control": _CACHE_CONTROL},
    )
