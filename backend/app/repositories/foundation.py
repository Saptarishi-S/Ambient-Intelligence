from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

from backend.app.core.database import Database
from backend.app.domain.models import DailyCalorieSummary, Detection, InventoryItem, Recipe, RecipeIngredient, ScanResult, UserProfile


def _load_json_list(value: str) -> list[str]:
    return json.loads(value or "[]")


class ProfileRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self) -> UserProfile:
        with self.database.session() as connection:
            row = connection.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
        if row is None:
            raise LookupError("Default profile not found.")
        return UserProfile(
            id=row["id"],
            name=row["name"],
            dietary_preference=row["dietary_preference"],
            allergens=_load_json_list(row["allergens_json"]),
            health_goal=row["health_goal"],
            calorie_target=row["calorie_target"],
            preference_tags=_load_json_list(row["preference_tags_json"]),
        )

    def update(self, profile: UserProfile) -> UserProfile:
        with self.database.session() as connection:
            connection.execute(
                """
                UPDATE user_profile
                SET
                    name = ?,
                    dietary_preference = ?,
                    allergens_json = ?,
                    health_goal = ?,
                    calorie_target = ?,
                    preference_tags_json = ?
                WHERE id = 1
                """,
                (
                    profile.name,
                    profile.dietary_preference,
                    json.dumps(profile.allergens),
                    profile.health_goal,
                    profile.calorie_target,
                    json.dumps(profile.preference_tags),
                ),
            )
            connection.commit()
        return self.get()

    def reset(self, profile: UserProfile) -> UserProfile:
        return self.update(profile)


class InventoryRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list(self) -> list[InventoryItem]:
        with self.database.session() as connection:
            rows = connection.execute(
                """
                SELECT id, name, quantity, unit, category, source, confidence, last_updated
                FROM inventory_items
                ORDER BY name ASC
                """
            ).fetchall()
        return [
            InventoryItem(
                id=row["id"],
                name=row["name"],
                quantity=row["quantity"],
                unit=row["unit"],
                category=row["category"],
                source=row["source"],
                confidence=row["confidence"],
                last_updated=row["last_updated"],
            )
            for row in rows
        ]

    def get(self, item_id: int) -> InventoryItem:
        with self.database.session() as connection:
            row = connection.execute(
                """
                SELECT id, name, quantity, unit, category, source, confidence, last_updated
                FROM inventory_items
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f"Inventory item {item_id} not found.")
        return InventoryItem(
            id=row["id"],
            name=row["name"],
            quantity=row["quantity"],
            unit=row["unit"],
            category=row["category"],
            source=row["source"],
            confidence=row["confidence"],
            last_updated=row["last_updated"],
        )

    def create(self, item: InventoryItem) -> InventoryItem:
        with self.database.session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO inventory_items (name, quantity, unit, category, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item.name, item.quantity, item.unit, item.category, item.source, item.confidence),
            )
            connection.commit()
            item_id = cursor.lastrowid
        return self.get(item_id)

    def update(self, item_id: int, item: InventoryItem) -> InventoryItem:
        with self.database.session() as connection:
            cursor = connection.execute(
                """
                UPDATE inventory_items
                SET
                    name = ?,
                    quantity = ?,
                    unit = ?,
                    category = ?,
                    source = ?,
                    confidence = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (item.name, item.quantity, item.unit, item.category, item.source, item.confidence, item_id),
            )
            connection.commit()
        if cursor.rowcount == 0:
            raise LookupError(f"Inventory item {item_id} not found.")
        return self.get(item_id)

    def delete(self, item_id: int) -> bool:
        with self.database.session() as connection:
            cursor = connection.execute("DELETE FROM inventory_items WHERE id = ?", (item_id,))
            connection.commit()
        return cursor.rowcount > 0

    def upsert_by_name(self, item: InventoryItem) -> InventoryItem:
        with self.database.session() as connection:
            row = connection.execute(
                """
                SELECT id, quantity
                FROM inventory_items
                WHERE LOWER(name) = LOWER(?)
                LIMIT 1
                """,
                (item.name,),
            ).fetchone()
            if row is None:
                cursor = connection.execute(
                    """
                    INSERT INTO inventory_items (name, quantity, unit, category, source, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (item.name, item.quantity, item.unit, item.category, item.source, item.confidence),
                )
                connection.commit()
                item_id = cursor.lastrowid
            else:
                connection.execute(
                    """
                    UPDATE inventory_items
                    SET
                        quantity = ?,
                        unit = ?,
                        category = ?,
                        source = ?,
                        confidence = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        row["quantity"] + item.quantity,
                        item.unit,
                        item.category,
                        item.source,
                        item.confidence,
                        row["id"],
                    ),
                )
                connection.commit()
                item_id = row["id"]
        return self.get(item_id)

    def replace_all(self, items: list[InventoryItem]) -> list[InventoryItem]:
        with self.database.session() as connection:
            connection.execute("DELETE FROM inventory_items")
            for item in items:
                connection.execute(
                    """
                    INSERT INTO inventory_items (name, quantity, unit, category, source, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (item.name, item.quantity, item.unit, item.category, item.source, item.confidence),
                )
            connection.commit()
        return self.list()


class RecipeRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list(self) -> list[Recipe]:
        with self.database.session() as connection:
            recipe_rows = connection.execute(
                """
                SELECT
                    id,
                    title,
                    description,
                    dietary_tags_json,
                    allergens_json,
                    preference_tags_json,
                    calories,
                    protein,
                    carbs,
                    fat,
                    prep_minutes,
                    instructions_json
                FROM recipes
                ORDER BY title ASC
                """
            ).fetchall()
            ingredient_rows = connection.execute(
                """
                SELECT recipe_id, name, quantity, unit, category, optional
                FROM recipe_ingredients
                ORDER BY recipe_id ASC, id ASC
                """
            ).fetchall()

        ingredients_by_recipe: dict[int, list[RecipeIngredient]] = {}
        for row in ingredient_rows:
            ingredients_by_recipe.setdefault(row["recipe_id"], []).append(
                RecipeIngredient(
                    name=row["name"],
                    quantity=row["quantity"],
                    unit=row["unit"],
                    category=row["category"],
                    optional=bool(row["optional"]),
                )
            )

        return [
            Recipe(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                dietary_tags=_load_json_list(row["dietary_tags_json"]),
                allergens=_load_json_list(row["allergens_json"]),
                preference_tags=_load_json_list(row["preference_tags_json"]),
                calories=row["calories"],
                protein=row["protein"],
                carbs=row["carbs"],
                fat=row["fat"],
                prep_minutes=row["prep_minutes"],
                instructions=_load_json_list(row["instructions_json"]),
                ingredients=ingredients_by_recipe.get(row["id"], []),
            )
            for row in recipe_rows
        ]


class MetadataRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_all(self) -> dict[str, list[dict[str, str | int]]]:
        with self.database.session() as connection:
            rows = connection.execute(
                """
                SELECT category, value, description, sort_order
                FROM reference_data
                ORDER BY category ASC, sort_order ASC
                """
            ).fetchall()

        grouped: dict[str, list[dict[str, str | int]]] = {}
        for row in rows:
            grouped.setdefault(row["category"], []).append(
                {
                    "value": row["value"],
                    "description": row["description"],
                    "sort_order": row["sort_order"],
                }
            )
        return grouped


class CaloriesRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_today(self) -> DailyCalorieSummary:
        today = date.today().isoformat()
        with self.database.session() as connection:
            row = connection.execute(
                """
                SELECT entry_date, consumed, burned
                FROM daily_calories
                WHERE entry_date = ?
                """,
                (today,),
            ).fetchone()
        if row is None:
            return DailyCalorieSummary(date=today, consumed=0, burned=0)
        return DailyCalorieSummary(date=row["entry_date"], consumed=row["consumed"], burned=row["burned"])

    def update_today(self, consumed: int, burned: int) -> DailyCalorieSummary:
        today = date.today().isoformat()
        with self.database.session() as connection:
            connection.execute(
                """
                INSERT INTO daily_calories (entry_date, consumed, burned)
                VALUES (?, ?, ?)
                ON CONFLICT(entry_date) DO UPDATE SET consumed = excluded.consumed, burned = excluded.burned
                """,
                (today, consumed, burned),
            )
            connection.commit()
        return self.get_today()

    def reset_today(self, consumed: int, burned: int) -> DailyCalorieSummary:
        return self.update_today(consumed=consumed, burned=burned)


class ScanRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(
        self,
        image_name: str,
        detections: list[Detection],
        image_mime_type: str | None = None,
        image_size_bytes: int | None = None,
        stored_image_path: str | None = None,
        detector: str = "mock-upload-v1",
        model_name: str | None = None,
        confidence_threshold: float | None = None,
    ) -> ScanResult:
        session_id = uuid4().hex
        with self.database.session() as connection:
            created_at = connection.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]
            connection.execute(
                """
                INSERT INTO scan_sessions (
                    session_id,
                    image_name,
                    created_at,
                    image_mime_type,
                    image_size_bytes,
                    stored_image_path,
                    detector,
                    model_name,
                    confidence_threshold
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    image_name,
                    created_at,
                    image_mime_type,
                    image_size_bytes,
                    stored_image_path,
                    detector,
                    model_name,
                    confidence_threshold,
                ),
            )
            for detection in detections:
                connection.execute(
                    """
                    INSERT INTO scan_detections (
                        session_id,
                        ingredient_name,
                        model_label,
                        confidence,
                        category,
                        quantity,
                        unit,
                        supported
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        detection.ingredient_name,
                        detection.model_label,
                        detection.confidence,
                        detection.category,
                        detection.quantity,
                        detection.unit,
                        int(detection.supported),
                    ),
                )
            connection.commit()
        return self.get(session_id)

    def get(self, session_id: str) -> ScanResult:
        with self.database.session() as connection:
            session_row = connection.execute(
                """
                SELECT
                    session_id,
                    image_name,
                    created_at,
                    image_mime_type,
                    image_size_bytes,
                    stored_image_path,
                    detector,
                    model_name,
                    confidence_threshold
                FROM scan_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            detection_rows = connection.execute(
                """
                SELECT ingredient_name, model_label, confidence, category, quantity, unit, supported
                FROM scan_detections
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        if session_row is None:
            raise LookupError(f"Scan session {session_id} not found.")
        detections = [
            Detection(
                ingredient_name=row["ingredient_name"],
                model_label=row["model_label"] or row["ingredient_name"],
                confidence=row["confidence"],
                category=row["category"],
                quantity=row["quantity"],
                unit=row["unit"],
                supported=bool(row["supported"]) if row["supported"] is not None else True,
            )
            for row in detection_rows
        ]
        return ScanResult(
            session_id=session_row["session_id"],
            image_name=session_row["image_name"],
            detections=detections,
            created_at=session_row["created_at"],
            image_mime_type=session_row["image_mime_type"],
            image_size_bytes=session_row["image_size_bytes"],
            image_url=session_row["stored_image_path"],
            detector=session_row["detector"] or "mock-upload-v1",
            model_name=session_row["model_name"],
            confidence_threshold=session_row["confidence_threshold"],
        )
