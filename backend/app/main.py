"""Entry point of the API: creates the FastAPI app and plugs in middleware, errors, and routes."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_error_handlers
from app.routers import activity, auth, dashboard, export, health, progress, projects, users

API_PREFIX = "/api"


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title="VanaTrack API", version="0.1.0")

    # CORS lets the browser allow our frontend (a different address) to call this API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(projects.router, prefix=API_PREFIX)
    app.include_router(progress.router, prefix=API_PREFIX)
    app.include_router(dashboard.router, prefix=API_PREFIX)
    app.include_router(activity.router, prefix=API_PREFIX)
    app.include_router(users.router, prefix=API_PREFIX)
    app.include_router(export.router, prefix=API_PREFIX)
    return app


app = create_app()
