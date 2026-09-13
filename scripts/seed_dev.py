"""Development seed data. Refuses to run without an explicit opt-in.

Replaced by the admin API in Phase 4 — this exists so the design can be
reviewed with real content instead of placeholders.
"""

import datetime as dt
import os
import sys

from app.db import SessionLocal
from app.models import (
    Certification, DsaProfile, Education, Experience, Project, SiteProfile,
    Skill, SocialLink,
)

if os.environ.get("SEED_DEV") != "yes":
    sys.exit("Refusing to seed: set SEED_DEV=yes to confirm.")

PROFILE = SiteProfile(
    id=1,
    name="Aviraj Khanchi",
    headline="Backend Engineer",
    location="Rohtak, India",
    email="you@example.com",
    bio="Recent ECE graduate from NSUT. I work mostly on backend systems in "
        "Java, Go and Python, and I like problems where correctness and "
        "latency both matter.",
)

PROJECTS = [
    Project(
        title="RedisGo", display_order=1, is_featured=True,
        summary="A Redis-compatible in-memory cache server written in Go.",
        tech_stack=["Go", "RESP protocol", "TCP"],
        highlights=["Speaks the RESP wire protocol, so redis-cli connects directly",
                    "Append-only persistence with ordered writes"],
        repo_url="https://github.com/AviK0928/redisgo",
    ),
    Project(
        title="Invoice Generator", display_order=2,
        summary="Spring Boot microservices invoicing system with Kafka messaging.",
        tech_stack=["Java", "Spring Boot", "Kafka", "PostgreSQL"],
        highlights=["Services communicate over Kafka topics rather than direct calls",
                    "Deployed on Render with Neon Postgres"],
        repo_url="https://github.com/AviK0928/Invoice-Generator",
    ),
    Project(
        title="SQL Query AI Agent", display_order=3,
        summary="A conversational agent that turns natural language into SQL.",
        tech_stack=["Python", "FastAPI", "LangChain"],
        highlights=["Query safety enforced in code, never in the prompt",
                    "Partial result sets are labelled so extrema aren't misreported"],
        repo_url="https://github.com/AviK0928/SQL_Query_AI_Agent",
    ),
]

EXPERIENCE = [
    Experience(
        display_order=1, kind="work", org="Rivigo", role="SDE Intern",
        location="On-site", start_date=dt.date(2026, 1, 1), end_date=dt.date(2026, 7, 1),
        bullets=["Worked on backend services and reporting pipelines."],
    ),
    Experience(
        display_order=2, kind="oss", org="AnkiDroid", role="Open source contributor",
        location="Remote", start_date=dt.date(2025, 5, 1), end_date=dt.date(2025, 12, 1),
        bullets=["Around 8 merged pull requests across documentation and UI fixes.",
                 "Took part in design and code review discussions."],
    ),
]

DSA = [
    DsaProfile(display_order=1, platform="LeetCode", handle="AviK0928",
               profile_url="https://leetcode.com/AviK0928"),
]

SKILLS = [
    Skill(display_order=i, category=c, name=n) for i, (c, n) in enumerate([
        ("Languages", "Java"), ("Languages", "Go"), ("Languages", "Python"),
        ("Backend", "Spring Boot"), ("Backend", "FastAPI"), ("Backend", "Kafka"),
        ("Data", "PostgreSQL"), ("Data", "Redis"),
        ("Infra", "AWS"), ("Infra", "Docker"), ("Infra", "Git"),
    ])
]

CERTS = [
    Certification(display_order=1, name="AWS Certified Cloud Practitioner",
                  issuer="Amazon Web Services"),
]

EDUCATION = [
    Education(display_order=1, institute="Netaji Subhas University of Technology",
              degree="B.Tech, Electronics and Communication",
              start_date=dt.date(2022, 11, 1), end_date=dt.date(2026, 6, 1),
              score="CGPA 8.21"),
]

SOCIALS = [
    SocialLink(display_order=1, platform="GitHub", url="https://github.com/AviK0928"),
    SocialLink(display_order=2, platform="LinkedIn", url="https://linkedin.com/in/"),
]

if __name__ == "__main__":
    session = SessionLocal()
    try:
        session.merge(PROFILE)
        for row in [*PROJECTS, *EXPERIENCE, *DSA, *SKILLS, *CERTS, *EDUCATION, *SOCIALS]:
            session.add(row)
        session.commit()
        print("Seeded.")
    finally:
        session.close()
