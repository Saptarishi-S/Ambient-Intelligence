from __future__ import annotations

import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

from backend.app.core.seed import seed_database


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    dietary_preference TEXT NOT NULL,
    allergens_json TEXT NOT NULL DEFAULT '[]',
    health_goal TEXT NOT NULL,
    calorie_target INTEGER NOT NULL,
    preference_tags_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 1,
    unit TEXT NOT NULL DEFAULT 'item',
    category TEXT NOT NULL DEFAULT 'pantry',
    source TEXT NOT NULL DEFAULT 'manual',
    confidence REAL,
    last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    dietary_tags_json TEXT NOT NULL,
    allergens_json TEXT NOT NULL,
    preference_tags_json TEXT NOT NULL,
    calories INTEGER NOT NULL,
    protein INTEGER NOT NULL,
    carbs INTEGER NOT NULL,
    fat INTEGER NOT NULL,
    prep_minutes INTEGER NOT NULL,
    instructions_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    category TEXT NOT NULL,
    optional INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS daily_calories (
    entry_date TEXT PRIMARY KEY,
    consumed INTEGER NOT NULL DEFAULT 0,
    burned INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reference_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    value TEXT NOT NULL,
    description TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    UNIQUE(category, value)
);

CREATE TABLE IF NOT EXISTS scan_sessions (
    session_id TEXT PRIMARY KEY,
    image_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    image_mime_type TEXT,
    image_size_bytes INTEGER,
    stored_image_path TEXT,
    detector TEXT NOT NULL DEFAULT 'mock-upload-v1',
    model_name TEXT,
    confidence_threshold REAL
);

CREATE TABLE IF NOT EXISTS scan_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ingredient_name TEXT NOT NULL,
    model_label TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL,
    category TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 1,
    unit TEXT NOT NULL DEFAULT 'item',
    supported INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (session_id) REFERENCES scan_sessions (session_id) ON DELETE CASCADE
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def session(self):
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.session() as connection:
            connection.executescript(SCHEMA_SQL)
            self._run_migrations(connection)
            seed_database(connection)
            connection.commit()

    def _run_migrations(self, connection: sqlite3.Connection) -> None:
        self._ensure_column(connection, "scan_sessions", "image_mime_type", "TEXT")
        self._ensure_column(connection, "scan_sessions", "image_size_bytes", "INTEGER")
        self._ensure_column(connection, "scan_sessions", "stored_image_path", "TEXT")
        self._ensure_column(connection, "scan_sessions", "detector", "TEXT NOT NULL DEFAULT 'mock-upload-v1'")
        self._ensure_column(connection, "scan_sessions", "model_name", "TEXT")
        self._ensure_column(connection, "scan_sessions", "confidence_threshold", "REAL")
        self._ensure_column(connection, "scan_detections", "model_label", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column(connection, "scan_detections", "supported", "INTEGER NOT NULL DEFAULT 1")

    @staticmethod
    def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        if any(row["name"] == column_name for row in rows):
            return
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def default_database_path() -> Path:
    configured_path = os.getenv("SMART_MEAL_PLANNER_DB_PATH")
    if configured_path:
        return Path(configured_path)

    return Path(tempfile.gettempdir()) / "SmartMealPlanner" / "smart_meal_planner.db"


def create_database(path: Path | None = None) -> Database:
    database = Database(path or default_database_path())
    database.initialize()
    return database
