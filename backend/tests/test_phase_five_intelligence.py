from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.core.database import Database
from backend.app.repositories.foundation import InventoryRepository, ProfileRepository, RecipeRepository, ScanRepository
from backend.app.services.detectors import DetectorConfigurationError, YoloDetector, bootstrap_detector, build_detector, normalize_yolo_label
from backend.app.services.inventory import InventoryService
from backend.app.services.profile import ProfileService
from backend.app.services.recommendations import RecommendationService
from backend.app.services.scans import ScanService


class StubScalar:
    def __init__(self, value: float) -> None:
        self.value = value

    def item(self) -> float:
        return self.value


class StubBox:
    def __init__(self, cls: int, confidence: float) -> None:
        self.cls = [StubScalar(cls)]
        self.conf = [StubScalar(confidence)]


class StubResult:
    def __init__(self, names: dict[int, str], boxes: list[StubBox]) -> None:
        self.names = names
        self.boxes = boxes


class StubModel:
    def __init__(self, results: list[StubResult]) -> None:
        self.results = results
        self.predict_calls: list[dict[str, object]] = []

    def predict(self, **kwargs: object) -> list[StubResult]:
        self.predict_calls.append(kwargs)
        return self.results


class PhaseFiveIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.database = Database(Path(self.temp_dir.name) / "smart_meal_planner.db")
        self.database.initialize()

        self.profile_repository = ProfileRepository(self.database)
        self.inventory_repository = InventoryRepository(self.database)
        self.recipe_repository = RecipeRepository(self.database)
        self.scan_repository = ScanRepository(self.database)

        self.profile_service = ProfileService(self.profile_repository)
        self.inventory_service = InventoryService(self.inventory_repository)
        self.recommendation_service = RecommendationService(
            self.recipe_repository,
            self.inventory_repository,
            self.profile_repository,
        )
        self.model_path = Path(self.temp_dir.name) / "YOLO_Model.pt"
        self.model_path.write_bytes(b"stub-model")

    def test_muscle_gain_goal_prefers_higher_protein_recipe(self) -> None:
        self.profile_service.update_profile(
            {
                "dietary_preference": "omnivore",
                "allergens": [],
                "health_goal": "muscle_gain",
                "calorie_target": 2400,
                "preference_tags": ["high_protein", "lunch"],
            }
        )
        for item in [
            {"name": "chicken breast", "quantity": 200, "unit": "g", "category": "protein"},
            {"name": "rice", "quantity": 1, "unit": "cup", "category": "grains"},
            {"name": "broccoli", "quantity": 1, "unit": "cup", "category": "produce"},
            {"name": "greek yogurt", "quantity": 1, "unit": "cup", "category": "dairy"},
            {"name": "berries", "quantity": 1, "unit": "cup", "category": "produce"},
            {"name": "oats", "quantity": 1, "unit": "cup", "category": "grains"},
        ]:
            self.inventory_service.create_item(item)

        recommendations = self.recommendation_service.recommend(limit=3)

        self.assertEqual(recommendations[0].recipe_title, "Chicken Rice Bowl")
        self.assertGreater(recommendations[0].protein_fit_score, recommendations[1].protein_fit_score)

    def test_recommendation_explanation_includes_macro_guidance(self) -> None:
        self.profile_service.update_profile(
            {
                "dietary_preference": "vegetarian",
                "allergens": [],
                "health_goal": "maintenance",
                "calorie_target": 2100,
                "preference_tags": ["balanced", "meal_prep"],
            }
        )
        for item in [
            {"name": "chickpeas", "quantity": 1, "unit": "cup", "category": "canned"},
            {"name": "rice", "quantity": 1, "unit": "cup", "category": "grains"},
            {"name": "cucumber", "quantity": 1, "unit": "item", "category": "produce"},
            {"name": "tomato", "quantity": 2, "unit": "item", "category": "produce"},
        ]:
            self.inventory_service.create_item(item)

        recommendation = self.recommendation_service.recommend(limit=1)[0]

        self.assertEqual(recommendation.narrative_style, "templated-nlg-v1")
        self.assertIn("macro balance", recommendation.explanation.lower())
        self.assertGreaterEqual(recommendation.macro_balance_score, 0)
        self.assertGreaterEqual(recommendation.calorie_fit_score, 0)

    def test_normalize_yolo_label_maps_aliases_and_support_flags(self) -> None:
        capsicum = normalize_yolo_label("capsicum")
        oren = normalize_yolo_label(" oren ")

        self.assertIsNotNone(capsicum)
        self.assertIsNotNone(oren)
        self.assertEqual(capsicum.ingredient_name, "bell pepper")
        self.assertTrue(capsicum.supported)
        self.assertEqual(oren.ingredient_name, "orange")
        self.assertFalse(oren.supported)
        self.assertIsNone(normalize_yolo_label("potato"))

    def test_yolo_detector_filters_threshold_and_ignored_labels(self) -> None:
        model = StubModel(
            [
                StubResult(
                    names={0: "capsicum", 1: "oren", 2: "potato", 3: "banana"},
                    boxes=[
                        StubBox(0, 0.91),
                        StubBox(1, 0.88),
                        StubBox(2, 0.97),
                        StubBox(3, 0.2),
                    ],
                )
            ]
        )
        detector = YoloDetector(
            model_path=str(self.model_path),
            confidence_threshold=0.35,
            model_loader=lambda _: model,
        )

        detections = detector.detect("phase-five-yolo.jpg", b"detector-threshold-demo")

        self.assertEqual(
            [(item.ingredient_name, item.model_label, item.supported) for item in detections],
            [("bell pepper", "capsicum", True), ("orange", "oren", False)],
        )
        self.assertEqual(model.predict_calls[0]["conf"], 0.35)

    def test_detector_factory_falls_back_to_mock_when_yolo_runtime_is_missing(self) -> None:
        previous_mode = os.environ.get("SMART_MEAL_PLANNER_DETECTOR")
        previous_model = os.environ.get("SMART_MEAL_PLANNER_YOLO_MODEL")
        os.environ["SMART_MEAL_PLANNER_DETECTOR"] = "yolo"
        os.environ["SMART_MEAL_PLANNER_YOLO_MODEL"] = str(self.model_path)
        self.addCleanup(self._restore_env, "SMART_MEAL_PLANNER_DETECTOR", previous_mode)
        self.addCleanup(self._restore_env, "SMART_MEAL_PLANNER_YOLO_MODEL", previous_model)

        def fake_find_spec(name: str):
            return None if name in {"torch", "ultralytics"} else object()

        with patch("backend.app.services.detectors.importlib.util.find_spec", side_effect=fake_find_spec):
            bootstrap = bootstrap_detector()
            detector = build_detector()

        self.assertEqual(bootstrap.requested_mode, "yolo")
        self.assertEqual(bootstrap.active_mode, "mock")
        self.assertIsNotNone(bootstrap.warning)
        self.assertEqual(bootstrap.detector.detector_name, "mock-upload-v2")
        self.assertEqual(detector.detector_name, "mock-upload-v2")

    def test_yolo_detector_fails_when_model_path_is_invalid(self) -> None:
        with self.assertRaises(DetectorConfigurationError):
            YoloDetector(model_path=str(Path(self.temp_dir.name) / "missing-model.pt"), model_loader=lambda _: StubModel([]))

    @staticmethod
    def _restore_env(key: str, previous_value: str | None) -> None:
        if previous_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous_value


if __name__ == "__main__":
    unittest.main()
