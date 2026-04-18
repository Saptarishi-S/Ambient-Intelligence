from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.dependencies import settings
from backend.app.api.error_handlers import register_error_handlers
from backend.app.api.routes.foundation import router as foundation_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.phase_two import router as phase_two_router


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Smart Meal Planner backend covering setup, reasoning, scan workflows, and demo controls.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.frontend_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(health_router)
app.include_router(foundation_router)
app.include_router(phase_two_router)
