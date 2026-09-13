from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    poolclass=NullPool,
    connect_args={"connect_timeout": _settings.db_connect_timeout},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _set_statement_timeout(dbapi_conn, _record) -> None:
    """Sent as a statement after connect.

    Neon's PgBouncer pooler rejects `statement_timeout` in the startup packet
    ("unsupported startup parameter in options"), so the extra round trip is
    mandatory on the pooled path. It costs ~1ms once the function is
    co-located with the database.
    """
    if engine.dialect.name != "postgresql":
        return
    with dbapi_conn.cursor() as cur:
        cur.execute(f"SET statement_timeout = {_settings.db_statement_timeout_ms}")


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
