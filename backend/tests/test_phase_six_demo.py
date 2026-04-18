from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.app.core.database import Database
from backend.app.repositories.foundation import CaloriesRepository, InventoryRepository, ProfileRepository, RecipeRepository
from backend.app.services.demo import DemoDataService
from backend.app.services.recommendations import RecommendationService


class PhaseSixDemoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.database = Database(Path(self.temp_dir.name) / "smart_meal_planner.db")
        self.database.initialize()

        self.profile_repository = ProfileRepository(self.database)
        self.inventory_repository = InventoryRepository(self.database)
        self.calories_repository = CaloriesRepository(self.database)
        self.recipe_repository = RecipeRepository(self.database)
        self.recommendation_service = RecommendationService(
            self.recipe_repository,
            self.inventory_repository,
            self.profile_repository,
        )
        self.demo_service = DemoDataService(
            self.profile_repository,
            self.inventory_repository,
            self.calories_repository,
            self.recommendation_service,
        )

    def test_list_scenarios_returns_seeded_demo_options(self) -> None:
        scenarios = self.demo_service.list_scenarios()

        self.assertGreaterEqual(len(scenarios), 3)
        self.assertIn("breakfast_boost", [item["id"] for item in scenarios])

    def test_load_scenario_updates_profile_inventory_and_recommendations(self) -> None:
        snapshot = self.demo_service.load_scenario("protein_recovery")

        self.assertEqual(snapshot["active_scenario"]["id"], "protein_recovery")
        self.assertEqual(snapshot["profile"]["health_goal"], "muscle_gain")
        self.assertTrue(any(item["name"] == "chicken breast" for item in snapshot["inventory"]))
        self.assertEqual(snapshot["recommendations"][0]["recipe_title"], "Chicken Rice Bowl")

    def test_reset_demo_restores_defaults_and_clears_inventory(self) -> None:
        self.demo_service.load_scenario("veggie_reset")
        snapshot = self.demo_service.reset_demo()

        self.assertEqual(snapshot["profile"]["health_goal"], "maintenance")
        self.assertEqual(snapshot["inventory"], [])
        self.assertEqual(snapshot["calories"]["consumed"], 1450)
        self.assertEqual(snapshot["calories"]["burned"], 520)


if __name__ == "__main__":
    unittest.main()
