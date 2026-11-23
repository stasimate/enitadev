"""FastAPI app factory for Enita."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from enita import __version__
from enita.api import exercises, topics
from enita.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Enita API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": __version__,
            "provider": settings.provider,
            "model": settings.model,
        }

    app.include_router(topics.router)
    app.include_router(exercises.router)

    # One image for production: FastAPI also serves the Angular build.
    # Mount it last, so that the /api routes have priority.
    if settings.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="frontend")

    return app


app = create_app()
