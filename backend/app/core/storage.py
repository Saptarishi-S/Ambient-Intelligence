from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4


def default_upload_root() -> Path:
    configured_path = os.getenv("SMART_MEAL_PLANNER_UPLOAD_DIR")
    if configured_path:
        return Path(configured_path)
    return Path(tempfile.gettempdir()) / "SmartMealPlanner" / "uploads"


def ensure_upload_root(path: Path | None = None) -> Path:
    upload_root = path or default_upload_root()
    upload_root.mkdir(parents=True, exist_ok=True)
    return upload_root


def build_upload_path(original_name: str, upload_root: Path | None = None) -> Path:
    root = ensure_upload_root(upload_root)
    source = Path(original_name or "fridge-upload.bin")
    suffix = source.suffix.lower() or ".bin"
    safe_stem = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in source.stem.lower()).strip("-")
    stem = safe_stem or "fridge-scan"
    return root / f"{stem}-{uuid4().hex[:10]}{suffix}"
