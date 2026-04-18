from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from backend.app.core.database import default_database_path
from backend.app.core.storage import default_upload_root


@dataclass(frozen=True, slots=True)
class AppSettings:
    app_name: str = "Smart Meal Planner API"
    version: str = "0.6.0"
    frontend_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
    max_upload_size_bytes: int = 5 * 1024 * 1024
    detector_mode: str = "mock"
    yolo_model_path: str | None = None
    yolo_confidence: float = 0.35
    database_path: str = str(default_database_path())
    upload_root: str = str(default_upload_root())


def _load_backend_env_file() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue

        cleaned_value = value.strip().strip("\"'")
        os.environ.setdefault(key, cleaned_value)


def get_settings() -> AppSettings:
    _load_backend_env_file()
    frontend_origins = tuple(
        origin.strip()
        for origin in os.getenv("SMART_MEAL_PLANNER_FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    )
    return AppSettings(
        frontend_origins=frontend_origins,
        max_upload_size_bytes=int(os.getenv("SMART_MEAL_PLANNER_MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024))),
        detector_mode=os.getenv("SMART_MEAL_PLANNER_DETECTOR", "mock").strip().lower(),
        yolo_model_path=(os.getenv("SMART_MEAL_PLANNER_YOLO_MODEL") or "").strip() or None,
        yolo_confidence=float(os.getenv("SMART_MEAL_PLANNER_YOLO_CONFIDENCE", "0.35")),
        database_path=str(default_database_path()),
        upload_root=str(default_upload_root()),
    )
