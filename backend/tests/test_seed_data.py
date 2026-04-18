from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.app.core.database import Database
from backend.app.repositories.foundation import CaloriesRepository, MetadataRepository, ProfileRepository, RecipeRepository


class SeedDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "smart_meal_planner.db"
        self.database = Database(self.database_path)
        self.database.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_default_profile_is_seeded(self) -> None:
        profile = ProfileRepository(self.database).get()
        self.assertEqual(profile.id, 1)
        self.assertEqual(profile.name, "Demo User")
        self.assertEqual(profile.health_goal, "maintenance")

    def test_reference_data_is_seeded(self) -> None:
        metadata = MetadataRepository(self.database).get_all()
        self.assertIn("ingredient_categories", metadata)
        self.assertIn("dietary_tags", metadata)
        self.assertIn("health_goals", metadata)
        self.assertGreaterEqual(len(metadata["ingredient_categories"]), 6)

    def test_recipes_are_seeded_with_ingredients(self) -> None:
        recipes = RecipeRepository(self.database).list()
        self.assertGreaterEqual(len(recipes), 5)
        self.assertTrue(all(recipe.ingredients for recipe in recipes))

    def test_today_calories_are_seeded(self) -> None:
        summary = CaloriesRepository(self.database).get_today()
        self.assertEqual(summary.consumed, 1450)
        self.assertEqual(summary.burned, 520)


if __name__ == "__main__":
    unittest.main()
