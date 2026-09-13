"""Admin write API. Every route requires a valid bearer token."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_session
from app.security import require_admin

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)

# name -> (ORM model, input schema, output schema)
_RESOURCES: dict[str, tuple[type, type[BaseModel], type[BaseModel]]] = {
    "social-links": (models.SocialLink, schemas.SocialLinkIn, schemas.SocialLinkOut),
    "projects": (models.Project, schemas.ProjectIn, schemas.ProjectOut),
    "experience": (models.Experience, schemas.ExperienceIn, schemas.ExperienceOut),
    "dsa-profiles": (models.DsaProfile, schemas.DsaProfileIn, schemas.DsaProfileOut),
    "blogs": (models.Blog, schemas.BlogIn, schemas.BlogOut),
    "skills": (models.Skill, schemas.SkillIn, schemas.SkillOut),
    "certifications": (models.Certification, schemas.CertificationIn, schemas.CertificationOut),
    "education": (models.Education, schemas.EducationIn, schemas.EducationOut),
}


def _resolve(resource: str):
    entry = _RESOURCES.get(resource)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown resource.")
    return entry


def _validate(schema: type[BaseModel], payload: dict) -> BaseModel:
    """Translate Pydantic errors into 422.

    FastAPI only converts ValidationError automatically for validation it runs
    during request parsing. Because the schema is chosen at runtime from the
    path, validation happens here instead — and an uncaught ValidationError
    would surface as a 500 with no indication of which field was wrong.
    """
    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(include_url=False),
        ) from exc


def _serialise(model_obj, schema: type[BaseModel]) -> dict:
    """Admin responses include id — you need it to update or delete the row."""
    return {"id": model_obj.id, **schema.model_validate(model_obj).model_dump(mode="json")}


@router.get("/{resource}")
def list_rows(resource: str, session: Session = Depends(get_session)):
    model, _in, out = _resolve(resource)
    stmt = select(model).order_by(model.display_order, model.id)
    rows = session.execute(stmt).scalars().all()
    return {"items": [_serialise(r, out) for r in rows]}


@router.post("/{resource}", status_code=status.HTTP_201_CREATED)
def create_row(resource: str, payload: dict, session: Session = Depends(get_session)):
    model, schema_in, out = _resolve(resource)
    data = _validate(schema_in, payload)
    row = model(**data.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return _serialise(row, out)


@router.put("/{resource}/{row_id}")
def replace_row(
    resource: str, row_id: int, payload: dict, session: Session = Depends(get_session)
):
    model, schema_in, out = _resolve(resource)
    row = session.get(model, row_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Row not found.")
    data = _validate(schema_in, payload)
    for field, value in data.model_dump().items():
        setattr(row, field, value)
    session.commit()
    session.refresh(row)
    return _serialise(row, out)


@router.delete("/{resource}/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_row(resource: str, row_id: int, session: Session = Depends(get_session)):
    model, _in, _out = _resolve(resource)
    row = session.get(model, row_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Row not found.")
    session.delete(row)
    session.commit()


@router.put("/profile")
def upsert_profile(payload: dict, session: Session = Depends(get_session)):
    """Singleton row, so PUT creates or replaces rather than POST."""
    data = _validate(schemas.ProfileIn, payload)
    row = session.get(models.SiteProfile, 1)
    if row is None:
        row = models.SiteProfile(id=1, **data.model_dump())
        session.add(row)
    else:
        for field, value in data.model_dump().items():
            setattr(row, field, value)
    session.commit()
    session.refresh(row)
    return _serialise(row, schemas.ProfileOut)
