"""Read-side data access. One query per section, all failures contained here."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SectionState(str, Enum):
    READY = "ready"          # content present
    EMPTY = "empty"          # queried fine, nothing published -> "Coming soon"
    UNAVAILABLE = "unavailable"  # query failed -> do not claim emptiness


@dataclass(frozen=True, slots=True)
class Section[T]:
    state: SectionState
    items: Sequence[T]

    @property
    def is_ready(self) -> bool:
        return self.state is SectionState.READY


def _fetch(session: Session, model: type[T]) -> Section[T]:
    """Published rows for one content table, ordered, with failures contained."""
    stmt = (
        select(model)
        .where(model.is_published.is_(True))
        .order_by(model.display_order, model.id)
    )
    try:
        items = tuple(session.execute(stmt).scalars().all())
    except SQLAlchemyError:
        logger.warning("section query failed: %s", model.__tablename__, exc_info=True)
        return Section(SectionState.UNAVAILABLE, ())
    return Section(SectionState.READY if items else SectionState.EMPTY, items)


def get_profile(session: Session) -> models.SiteProfile | None:
    try:
        return session.get(models.SiteProfile, 1)
    except SQLAlchemyError:
        logger.warning("profile query failed", exc_info=True)
        return None


def get_social_links(session: Session) -> Section[models.SocialLink]:
    return _fetch(session, models.SocialLink)


def get_projects(session: Session) -> Section[models.Project]:
    return _fetch(session, models.Project)


def get_experience(session: Session) -> Section[models.Experience]:
    return _fetch(session, models.Experience)


def get_dsa_profiles(session: Session) -> Section[models.DsaProfile]:
    return _fetch(session, models.DsaProfile)


def get_blogs(session: Session) -> Section[models.Blog]:
    return _fetch(session, models.Blog)


def get_skills(session: Session) -> Section[models.Skill]:
    return _fetch(session, models.Skill)


def get_certifications(session: Session) -> Section[models.Certification]:
    return _fetch(session, models.Certification)


def get_education(session: Session) -> Section[models.Education]:
    return _fetch(session, models.Education)
