from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ContentMixin(TimestampMixin):
    """Every listable content table shares these three columns."""

    id: Mapped[int] = mapped_column(primary_key=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class SiteProfile(Base, TimestampMixin):
    __tablename__ = "site_profile"

    id: Mapped[int] = mapped_column(primary_key=True)  # always 1
    name: Mapped[str] = mapped_column(String(120))
    headline: Mapped[str] = mapped_column(String(200))
    bio: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(200))
    resume_url: Mapped[str | None] = mapped_column(String(500))


class SocialLink(Base, ContentMixin):
    __tablename__ = "social_links"

    platform: Mapped[str] = mapped_column(String(60))
    url: Mapped[str] = mapped_column(String(500))
    icon: Mapped[str | None] = mapped_column(String(60))


class Project(Base, ContentMixin):
    __tablename__ = "projects"

    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text)
    tech_stack: Mapped[list[str]] = mapped_column(JSON, default=list)
    highlights: Mapped[list[str]] = mapped_column(JSON, default=list)
    repo_url: Mapped[str | None] = mapped_column(String(500))
    live_url: Mapped[str | None] = mapped_column(String(500))
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)


class Experience(Base, ContentMixin):
    __tablename__ = "experience"

    org: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(30), default="work")  # work | oss
    location: Mapped[str | None] = mapped_column(String(120))
    start_date: Mapped[dt.date] = mapped_column(Date)
    end_date: Mapped[dt.date | None] = mapped_column(Date)
    bullets: Mapped[list[str]] = mapped_column(JSON, default=list)


class DsaProfile(Base, ContentMixin):
    __tablename__ = "dsa_profiles"

    platform: Mapped[str] = mapped_column(String(60))
    handle: Mapped[str] = mapped_column(String(120))
    profile_url: Mapped[str] = mapped_column(String(500))
    rating: Mapped[int | None] = mapped_column(Integer)
    problems_solved: Mapped[int | None] = mapped_column(Integer)
    badge: Mapped[str | None] = mapped_column(String(80))
    last_synced_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class Blog(Base, ContentMixin):
    __tablename__ = "blogs"

    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[dt.date | None] = mapped_column(Date)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)


class Skill(Base, ContentMixin):
    __tablename__ = "skills"

    category: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(80))


class Certification(Base, ContentMixin):
    __tablename__ = "certifications"

    name: Mapped[str] = mapped_column(String(200))
    issuer: Mapped[str] = mapped_column(String(160))
    issued_on: Mapped[dt.date | None] = mapped_column(Date)
    credential_url: Mapped[str | None] = mapped_column(String(500))


class Education(Base, ContentMixin):
    __tablename__ = "education"

    institute: Mapped[str] = mapped_column(String(200))
    degree: Mapped[str] = mapped_column(String(200))
    start_date: Mapped[dt.date | None] = mapped_column(Date)
    end_date: Mapped[dt.date | None] = mapped_column(Date)
    score: Mapped[str | None] = mapped_column(String(60))
