from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Free-HR API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
