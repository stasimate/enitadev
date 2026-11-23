"""FastAPI app factory for Enita."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from enita import __version__
from enita.settings import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="Enita API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        s = get_settings()
        return {"status": "ok", "version": __version__, "provider": s.provider, "model": s.model}

    return app


app = create_app()
