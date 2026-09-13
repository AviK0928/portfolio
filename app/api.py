"""Public read-only JSON API. No authentication — everything here is public."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app import repository as repo
from app import schemas
from app.config import get_settings
from app.db import get_session

router = APIRouter(prefix="/api/v1", tags=["public"])

_settings = get_settings()

_SECTIONS = {
    "social-links": (repo.get_social_links, schemas.SocialLinkOut),
    "projects": (repo.get_projects, schemas.ProjectOut),
    "experience": (repo.get_experience, schemas.ExperienceOut),
    "dsa-profiles": (repo.get_dsa_profiles, schemas.DsaProfileOut),
    "blogs": (repo.get_blogs, schemas.BlogOut),
    "skills": (repo.get_skills, schemas.SkillOut),
    "certifications": (repo.get_certifications, schemas.CertificationOut),
    "education": (repo.get_education, schemas.EducationOut),
}


def _cache(response: Response) -> None:
    """Edge-cache reads. This is what keeps the site up when Neon is cold or down."""
    response.headers["Cache-Control"] = (
        f"public, s-maxage={_settings.public_cache_seconds}, "
        f"stale-while-revalidate=86400"
    )


@router.get("/profile")
def read_profile(response: Response, session: Session = Depends(get_session)):
    _cache(response)
    profile = repo.get_profile(session)
    if profile is None:
        return {"state": "empty", "item": None}
    return {"state": "ready", "item": schemas.ProfileOut.model_validate(profile)}


@router.get("/sections/{name}")
def read_section(name: str, response: Response, session: Session = Depends(get_session)):
    _cache(response)
    entry = _SECTIONS.get(name)
    if entry is None:
        return Response(status_code=404)
    fetch, schema = entry
    section = fetch(session)
    return {
        "state": section.state.value,
        "items": [schema.model_validate(i) for i in section.items],
    }
