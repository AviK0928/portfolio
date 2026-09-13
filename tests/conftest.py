import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base


@pytest.fixture()
def db_engine():
    """In-memory SQLite shared across threads.

    TestClient runs the app on a separate portal thread. With the default
    SingletonThreadPool each thread gets its own connection — and for
    `sqlite://` a separate connection means a separate, empty database.
    StaticPool holds one connection for all threads, so the app under test
    sees the tables this fixture created.
    """
    eng = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(db_engine):
    s = sessionmaker(bind=db_engine, expire_on_commit=False)()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(db_engine):
    """App wired to the test DB, with the real get_session dependency overridden."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.db import get_session
    from app.main import app

    TestSession = sessionmaker(bind=db_engine, expire_on_commit=False)

    def _override():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
