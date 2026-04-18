from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.app.core.database import Database
from backend.app.repositories.foundation import CaloriesRepository, InventoryRepository, ProfileRepository, RecipeRepository, ScanRepository
from backend.app.services.calories import CaloriesService
from backend.app.services.inventory import InventoryService
from backend.app.services.profile import ProfileService
from backend.app.services.recommendations import RecommendationService
from backend.app.services.scans import ScanService
from backend.app.services.shopping import ShoppingListService


class PhaseTwoServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "smart_meal_planner.db")
        self.database.initialize()

        self.profile_repository = ProfileRepository(self.database)
        self.inventory_repository = InventoryRepository(self.database)
        self.recipe_repository = RecipeRepository(self.database)
        self.scan_repository = ScanRepository(self.database)
        self.calories_repository = CaloriesRepository(self.database)

        self.profile_service = ProfileService(self.profile_repository)
        self.inventory_service = InventoryService(self.inventory_repository)
        self.recommendation_service = RecommendationService(
            self.recipe_repository,
            self.inventory_repository,
            self.profile_repository,
        )
        self.shopping_service = ShoppingListService(self.recipe_repository, self.recommendation_service)
        self.scan_service = ScanService(self.scan_repository, self.inventory_service)
        self.calories_service = CaloriesService(self.calories_repository)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_profile_update_persists_normalized_values(self) -> None:
        profile = self.profile_service.update_profile(
            {
                "name": "Aditi",
                "dietary_preference": "vegetarian",
                "allergens": ["Dairy", " dairy ", "Soy"],
                "health_goal": "weight_loss",
                "calorie_target": 1800,
                "preference_tags": ["Quick", " quick ", "Breakfast"],
            }
        )

        self.assertEqual(profile.name, "Aditi")
        self.assertEqual(profile.dietary_preference, "vegetarian")
        self.assertEqual(profile.allergens, ["dairy", "soy"])
        self.assertEqual(profile.preference_tags, ["breakfast", "quick"])

    def test_inventory_crud_round_trip(self) -> None:
        created = self.inventory_service.create_item(
            {"name": "Rice", "quantity": 1, "unit": "cup", "category": "grains"}
        )
        updated = self.inventory_service.update_item(created.id, {"quantity": 2, "category": "pantry"})
        deleted = self.inventory_service.delete_item(created.id)

        self.assertEqual(created.name, "rice")
        self.assertEqual(updated.quantity, 2)
        self.assertEqual(updated.category, "pantry")
        self.assertTrue(deleted)
        self.assertEqual(self.inventory_service.list_inventory(), [])

    def test_recommendations_filter_and_rank_using_inventory_and_profile(self) -> None:
        self.profile_service.update_profile(
            {
                "dietary_preference": "vegetarian",
                "allergens": ["dairy"],
                "health_goal": "maintenance",
                "preference_tags": ["balanced", "meal_prep"],
            }
        )
        for item in [
            {"name": "Chickpeas", "quantity": 1, "unit": "cup", "category": "canned"},
            {"name": "Rice", "quantity": 1, "unit": "cup", "category": "grains"},
            {"name": "Cucumber", "quantity": 1, "unit": "item", "category": "produce"},
            {"name": "Tomato", "quantity": 2, "unit": "item", "category": "produce"},
        ]:
            self.inventory_service.create_item(item)

        recommendations = self.recommendation_service.recommend(limit=5)

        self.assertTrue(recommendations)
        self.assertEqual(recommendations[0].recipe_title, "Chickpea Buddha Bowl")
        self.assertNotIn("Spinach Omelette", [item.recipe_title for item in recommendations])
        self.assertNotIn("Greek Yogurt Parfait", [item.recipe_title for item in recommendations])
        self.assertTrue(recommendations[0].score > recommendations[-1].score)

    def test_scan_confirmation_upserts_inventory_without_duplicate_rows(self) -> None:
        tomato = self.inventory_service.create_item(
            {"name": "Tomato", "quantity": 1, "unit": "item", "category": "produce"}
        )
        scan = self.scan_service.scan_image("generic-fridge.jpg")
        result = self.scan_service.confirm_scan(scan.session_id, ["tomato", "cucumber"])
        inventory = self.inventory_service.list_inventory()
        tomato_item = next(item for item in inventory if item.name == "tomato")

        self.assertEqual(tomato.id, tomato_item.id)
        self.assertEqual(tomato_item.quantity, 3)
        self.assertEqual(sorted(item.name for item in inventory), ["cucumber", "tomato"])
        self.assertEqual(sorted(item.ingredient_name for item in result["accepted"]), ["cucumber", "tomato"])

    def test_shopping_list_groups_missing_items_for_selected_recipe(self) -> None:
        self.profile_service.update_profile(
            {
                "dietary_preference": "vegetarian",
                "allergens": [],
                "preference_tags": ["quick", "breakfast"],
            }
        )
        self.inventory_service.create_item({"name": "Egg", "quantity": 3, "unit": "item", "category": "protein"})
        self.inventory_service.create_item({"name": "Spinach", "quantity": 1, "unit": "cup", "category": "produce"})

        omelette = next(recipe for recipe in self.recipe_repository.list() if recipe.title == "Spinach Omelette")
        shopping_list = self.shopping_service.build_list(recipe_ids=[omelette.id])

        self.assertIn("dairy", shopping_list)
        self.assertEqual(shopping_list["dairy"][0].name, "cheese")

    def test_calorie_summary_updates_for_today(self) -> None:
        summary = self.calories_service.update_today_summary({"consumed": 1700, "burned": 650})
        self.assertEqual(summary.consumed, 1700)
        self.assertEqual(summary.burned, 650)


if __name__ == "__main__":
    unittest.main()
