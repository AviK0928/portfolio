"""API response shapes. Deliberately separate from ORM models."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProfileOut(_Out):
    name: str
    headline: str
    bio: str | None = None
    location: str | None = None
    email: str | None = None
    resume_url: str | None = None


class SocialLinkOut(_Out):
    platform: str
    url: str
    icon: str | None = None


class ProjectOut(_Out):
    title: str
    summary: str
    tech_stack: list[str] = []
    highlights: list[str] = []
    repo_url: str | None = None
    live_url: str | None = None
    is_featured: bool = False


class ExperienceOut(_Out):
    org: str
    role: str
    kind: str
    location: str | None = None
    start_date: dt.date
    end_date: dt.date | None = None
    bullets: list[str] = []


class DsaProfileOut(_Out):
    platform: str
    handle: str
    profile_url: str
    rating: int | None = None
    problems_solved: int | None = None
    badge: str | None = None
    last_synced_at: dt.datetime | None = None


class BlogOut(_Out):
    title: str
    url: str
    summary: str | None = None
    published_at: dt.date | None = None
    tags: list[str] = []


class SkillOut(_Out):
    category: str
    name: str


class CertificationOut(_Out):
    name: str
    issuer: str
    issued_on: dt.date | None = None
    credential_url: str | None = None


class EducationOut(_Out):
    institute: str
    degree: str
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    score: str | None = None


class SectionOut[T](_Out):
    state: str
    items: list[T]
