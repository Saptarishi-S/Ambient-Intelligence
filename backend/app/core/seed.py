from __future__ import annotations

import json
import sqlite3
from datetime import date

from backend.app.domain.models import DietaryPreference, HealthGoal


REFERENCE_DATA = {
    "ingredient_categories": [
        ("produce", "Fresh fruits and vegetables"),
        ("dairy", "Milk, cheese, and cultured products"),
        ("protein", "Meat, seafood, tofu, and eggs"),
        ("grains", "Rice, pasta, bread, and cereals"),
        ("pantry", "Shelf-stable basics"),
        ("condiments", "Sauces, oils, and seasonings"),
        ("canned", "Canned ingredients"),
        ("frozen", "Frozen ingredients"),
    ],
    "dietary_tags": [
        (DietaryPreference.OMNIVORE.value, "Suitable for general diets"),
        (DietaryPreference.VEGETARIAN.value, "Excludes meat and fish"),
        (DietaryPreference.VEGAN.value, "Excludes all animal products"),
        (DietaryPreference.PESCATARIAN.value, "Allows seafood but not meat"),
    ],
    "health_goals": [
        (HealthGoal.WEIGHT_LOSS.value, "Prioritize lighter meals"),
        (HealthGoal.MAINTENANCE.value, "Balance calories and variety"),
        (HealthGoal.MUSCLE_GAIN.value, "Prioritize protein-rich meals"),
    ],
}


DEFAULT_PROFILE = {
    "id": 1,
    "name": "Demo User",
    "dietary_preference": DietaryPreference.OMNIVORE.value,
    "allergens": [],
    "health_goal": HealthGoal.MAINTENANCE.value,
    "calorie_target": 2200,
    "preference_tags": ["quick", "balanced"],
}


RECIPE_SEEDS = [
    {
        "title": "Spinach Omelette",
        "description": "A quick vegetarian breakfast with spinach and cheese.",
        "dietary_tags": [DietaryPreference.VEGETARIAN.value],
        "allergens": ["egg", "dairy"],
        "preference_tags": ["quick", "high_protein", "breakfast"],
        "calories": 390,
        "protein": 25,
        "carbs": 8,
        "fat": 28,
        "prep_minutes": 12,
        "instructions": [
            "Whisk eggs with a pinch of salt.",
            "Saute spinach briefly in a pan.",
            "Add eggs and cook until nearly set.",
            "Top with cheese, fold, and serve.",
        ],
        "ingredients": [
            {"name": "egg", "quantity": 3, "unit": "item", "category": "protein", "optional": False},
            {"name": "spinach", "quantity": 1, "unit": "cup", "category": "produce", "optional": False},
            {"name": "cheese", "quantity": 0.25, "unit": "cup", "category": "dairy", "optional": False},
            {"name": "olive oil", "quantity": 1, "unit": "tbsp", "category": "condiments", "optional": True},
        ],
    },
    {
        "title": "Chickpea Buddha Bowl",
        "description": "A fiber-rich vegan bowl with chickpeas, rice, and vegetables.",
        "dietary_tags": [DietaryPreference.VEGAN.value, DietaryPreference.VEGETARIAN.value],
        "allergens": [],
        "preference_tags": ["meal_prep", "balanced", "high_fiber"],
        "calories": 510,
        "protein": 19,
        "carbs": 68,
        "fat": 17,
        "prep_minutes": 20,
        "instructions": [
            "Warm cooked rice and roasted chickpeas.",
            "Slice cucumber and tomatoes.",
            "Arrange bowl components and drizzle dressing.",
        ],
        "ingredients": [
            {"name": "chickpeas", "quantity": 1, "unit": "cup", "category": "canned", "optional": False},
            {"name": "rice", "quantity": 1, "unit": "cup", "category": "grains", "optional": False},
            {"name": "cucumber", "quantity": 0.5, "unit": "item", "category": "produce", "optional": False},
            {"name": "tomato", "quantity": 1, "unit": "item", "category": "produce", "optional": False},
        ],
    },
    {
        "title": "Chicken Rice Bowl",
        "description": "A balanced lunch bowl with grilled chicken and broccoli.",
        "dietary_tags": [DietaryPreference.OMNIVORE.value],
        "allergens": [],
        "preference_tags": ["balanced", "high_protein", "lunch"],
        "calories": 610,
        "protein": 42,
        "carbs": 48,
        "fat": 24,
        "prep_minutes": 25,
        "instructions": [
            "Cook rice according to package directions.",
            "Sear chicken until fully cooked.",
            "Steam broccoli and serve together.",
        ],
        "ingredients": [
            {"name": "chicken breast", "quantity": 200, "unit": "g", "category": "protein", "optional": False},
            {"name": "rice", "quantity": 1, "unit": "cup", "category": "grains", "optional": False},
            {"name": "broccoli", "quantity": 1, "unit": "cup", "category": "produce", "optional": False},
        ],
    },
    {
        "title": "Greek Yogurt Parfait",
        "description": "A layered yogurt breakfast with fruit and oats.",
        "dietary_tags": [DietaryPreference.VEGETARIAN.value],
        "allergens": ["dairy"],
        "preference_tags": ["breakfast", "quick", "high_protein"],
        "calories": 320,
        "protein": 20,
        "carbs": 35,
        "fat": 9,
        "prep_minutes": 8,
        "instructions": [
            "Layer yogurt, berries, and oats in a glass.",
            "Top with honey if desired.",
        ],
        "ingredients": [
            {"name": "greek yogurt", "quantity": 1, "unit": "cup", "category": "dairy", "optional": False},
            {"name": "berries", "quantity": 0.5, "unit": "cup", "category": "produce", "optional": False},
            {"name": "oats", "quantity": 0.25, "unit": "cup", "category": "grains", "optional": False},
        ],
    },
    {
        "title": "Tofu Stir Fry",
        "description": "A quick tofu and vegetable stir fry for weeknight dinners.",
        "dietary_tags": [DietaryPreference.VEGAN.value, DietaryPreference.VEGETARIAN.value],
        "allergens": ["soy"],
        "preference_tags": ["quick", "balanced", "dinner"],
        "calories": 430,
        "protein": 23,
        "carbs": 29,
        "fat": 24,
        "prep_minutes": 18,
        "instructions": [
            "Saute tofu until golden.",
            "Add mixed vegetables and stir-fry sauce.",
            "Cook until vegetables are tender-crisp.",
        ],
        "ingredients": [
            {"name": "tofu", "quantity": 200, "unit": "g", "category": "protein", "optional": False},
            {"name": "bell pepper", "quantity": 1, "unit": "item", "category": "produce", "optional": False},
            {"name": "broccoli", "quantity": 1, "unit": "cup", "category": "produce", "optional": False},
            {"name": "soy sauce", "quantity": 1, "unit": "tbsp", "category": "condiments", "optional": True},
        ],
    },
]


def seed_database(connection: sqlite3.Connection) -> None:
    seed_reference_data(connection)
    seed_default_profile(connection)
    seed_recipes(connection)
    seed_today_calories(connection)


def seed_reference_data(connection: sqlite3.Connection) -> None:
    for category, rows in REFERENCE_DATA.items():
        for index, (value, description) in enumerate(rows, start=1):
            connection.execute(
                """
                INSERT OR IGNORE INTO reference_data (category, value, description, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (category, value, description, index),
            )


def seed_default_profile(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO user_profile (
            id,
            name,
            dietary_preference,
            allergens_json,
            health_goal,
            calorie_target,
            preference_tags_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            DEFAULT_PROFILE["id"],
            DEFAULT_PROFILE["name"],
            DEFAULT_PROFILE["dietary_preference"],
            json.dumps(DEFAULT_PROFILE["allergens"]),
            DEFAULT_PROFILE["health_goal"],
            DEFAULT_PROFILE["calorie_target"],
            json.dumps(DEFAULT_PROFILE["preference_tags"]),
        ),
    )


def seed_recipes(connection: sqlite3.Connection) -> None:
    recipe_count = connection.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    if recipe_count:
        return

    for recipe in RECIPE_SEEDS:
        cursor = connection.execute(
            """
            INSERT INTO recipes (
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
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recipe["title"],
                recipe["description"],
                json.dumps(recipe["dietary_tags"]),
                json.dumps(recipe["allergens"]),
                json.dumps(recipe["preference_tags"]),
                recipe["calories"],
                recipe["protein"],
                recipe["carbs"],
                recipe["fat"],
                recipe["prep_minutes"],
                json.dumps(recipe["instructions"]),
            ),
        )
        recipe_id = cursor.lastrowid
        for ingredient in recipe["ingredients"]:
            connection.execute(
                """
                INSERT INTO recipe_ingredients (
                    recipe_id,
                    name,
                    quantity,
                    unit,
                    category,
                    optional
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe_id,
                    ingredient["name"],
                    ingredient["quantity"],
                    ingredient["unit"],
                    ingredient["category"],
                    int(ingredient["optional"]),
                ),
            )


def seed_today_calories(connection: sqlite3.Connection) -> None:
    today = date.today().isoformat()
    connection.execute(
        """
        INSERT OR IGNORE INTO daily_calories (entry_date, consumed, burned)
        VALUES (?, ?, ?)
        """,
        (today, 1450, 520),
    )

