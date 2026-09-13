from fastapi import FastAPI
from sqlalchemy import text

from app.api import router as public_router
from app.db import engine


def create_app() -> FastAPI:
    app = FastAPI(title="Portfolio", docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(public_router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        db_status = "ok"
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            db_status = "unavailable"
        return {"app": "ok", "db": db_status}

    return app


app = create_app()
