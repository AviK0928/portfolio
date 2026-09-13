from sqlalchemy import create_engine

from app.models import Base


def test_healthz_reports_app_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["app"] == "ok"


def test_healthz_never_500s_when_db_unreachable(client, monkeypatch):
    import app.main as main

    broken = create_engine("postgresql+psycopg://nobody@127.0.0.1:1/none")
    monkeypatch.setattr(main, "engine", broken)

    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"app": "ok", "db": "unavailable"}


def test_schema_creates_on_sqlite():
    """Guards the JSON-over-ARRAY choice: models must stay dialect-portable."""
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    assert "projects" in Base.metadata.tables
    assert "dsa_profiles" in Base.metadata.tables
