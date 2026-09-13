"""Create all tables. Idempotent: existing tables are left alone."""

from app.db import engine
from app.models import Base

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Schema created/verified on:", engine.url.render_as_string(hide_password=True))
