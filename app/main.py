from fastapi import FastAPI
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.api import router as public_router
from app.config import get_settings
from app.db import engine
from app.pages import router as pages_router


def create_app() -> FastAPI:
    app = FastAPI(title="Portfolio", docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(public_router)
    app.include_router(pages_router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        db_status = "ok"
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            db_status = "unavailable"
        return {"app": "ok", "db": db_status}

    if get_settings().debug:
        # On Vercel, public/ is served by the CDN and never reaches this function.
        # This route exists only so `uvicorn` serves the same URL locally.
        @app.get("/styles.css", include_in_schema=False)
        def _styles() -> FileResponse:
            return FileResponse("public/styles.css", media_type="text/css")

    return app


app = create_app()
