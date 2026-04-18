from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.dependencies import get_detector_runtime_status, settings


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str | int | None]:
    response: dict[str, str | int | None] = {
        "status": "ok",
        "version": settings.version,
        "max_upload_size_bytes": settings.max_upload_size_bytes,
    }
    response.update(get_detector_runtime_status())
    return response
