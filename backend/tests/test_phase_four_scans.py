from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.app.core.database import Database
from backend.app.repositories.foundation import InventoryRepository, ProfileRepository, RecipeRepository, ScanRepository
from backend.app.services.detectors import YoloDetector
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

    def predict(self, **_: object) -> list[StubResult]:
        return self.results


class PhaseFourScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.previous_upload_dir = os.environ.get("SMART_MEAL_PLANNER_UPLOAD_DIR")
        os.environ["SMART_MEAL_PLANNER_UPLOAD_DIR"] = str(Path(self.temp_dir.name) / "uploads")
        self.addCleanup(self._restore_upload_dir)

        self.database = Database(Path(self.temp_dir.name) / "smart_meal_planner.db")
        self.database.initialize()
        self.inventory_repository = InventoryRepository(self.database)
        self.profile_repository = ProfileRepository(self.database)
        self.recipe_repository = RecipeRepository(self.database)
        self.scan_repository = ScanRepository(self.database)

        self.inventory_service = InventoryService(self.inventory_repository)
        self.profile_service = ProfileService(self.profile_repository)
        self.recommendation_service = RecommendationService(
            self.recipe_repository,
            self.inventory_repository,
            self.profile_repository,
        )
        self.scan_service = ScanService(self.scan_repository, self.inventory_service)
        self.model_path = Path(self.temp_dir.name) / "YOLO_Model.pt"
        self.model_path.write_bytes(b"stub-model")

    def _restore_upload_dir(self) -> None:
        if self.previous_upload_dir is None:
            os.environ.pop("SMART_MEAL_PLANNER_UPLOAD_DIR", None)
        else:
            os.environ["SMART_MEAL_PLANNER_UPLOAD_DIR"] = self.previous_upload_dir

    def test_scan_upload_persists_image_metadata_and_file(self) -> None:
        scan = self.scan_service.scan_upload(
            image_name="veggie-fridge.jpg",
            image_bytes=b"phase-four-demo-bytes",
            image_mime_type="image/jpeg",
        )

        image_path = self.scan_service.get_image_path(scan.session_id)

        self.assertEqual(scan.image_mime_type, "image/jpeg")
        self.assertEqual(scan.image_size_bytes, len(b"phase-four-demo-bytes"))
        self.assertEqual(scan.image_url, f"/scan/{scan.session_id}/image")
        self.assertTrue(image_path.exists())
        self.assertEqual(image_path.suffix, ".jpg")

    def test_yolo_scan_upload_persists_detector_metadata_and_normalized_detections(self) -> None:
        detector = YoloDetector(
            model_path=str(self.model_path),
            confidence_threshold=0.35,
            model_loader=lambda _: StubModel(
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
            ),
        )
        scan_service = ScanService(self.scan_repository, self.inventory_service, detector=detector)

        scan = scan_service.scan_upload(
            image_name="real-fridge.jpg",
            image_bytes=b"phase-four-yolo-demo",
            image_mime_type="image/jpeg",
        )

        self.assertEqual(scan.detector, "yolo-ultralytics-v1")
        self.assertEqual(scan.model_name, "YOLO_Model.pt")
        self.assertEqual(scan.confidence_threshold, 0.35)
        self.assertEqual(
            [(item.ingredient_name, item.model_label, item.supported) for item in scan.detections],
            [("bell pepper", "capsicum", True), ("orange", "oren", False)],
        )

    def test_uploaded_scan_confirmation_feeds_recommendations(self) -> None:
        self.profile_service.update_profile(
            {
                "dietary_preference": "omnivore",
                "allergens": [],
                "health_goal": "maintenance",
                "preference_tags": ["balanced", "lunch"],
            }
        )

        scan = self.scan_service.scan_upload(
            image_name="protein-fridge.png",
            image_bytes=b"phase-four-protein-demo",
            image_mime_type="image/png",
        )
        self.scan_service.confirm_scan(scan.session_id, ["chicken breast", "rice", "broccoli"])

        recommendations = self.recommendation_service.recommend(limit=3)

        self.assertTrue(recommendations)
        self.assertEqual(recommendations[0].recipe_title, "Chicken Rice Bowl")
        self.assertIn("chicken breast", recommendations[0].matched_ingredients)
        self.assertIn("rice", recommendations[0].matched_ingredients)
        self.assertIn("broccoli", recommendations[0].matched_ingredients)

    def test_confirm_scan_only_promotes_supported_yolo_detections(self) -> None:
        for item in [
            {"name": "tofu", "quantity": 200, "unit": "g", "category": "protein"},
            {"name": "broccoli", "quantity": 1, "unit": "cup", "category": "produce"},
        ]:
            self.inventory_service.create_item(item)

        detector = YoloDetector(
            model_path=str(self.model_path),
            confidence_threshold=0.35,
            model_loader=lambda _: StubModel(
                [
                    StubResult(
                        names={0: "capsicum", 1: "oren"},
                        boxes=[StubBox(0, 0.92), StubBox(1, 0.86)],
                    )
                ]
            ),
        )
        scan_service = ScanService(self.scan_repository, self.inventory_service, detector=detector)
        scan = scan_service.scan_upload(
            image_name="fridge-confirm.jpg",
            image_bytes=b"phase-four-confirm-demo",
            image_mime_type="image/jpeg",
        )

        confirmation = scan_service.confirm_scan(scan.session_id, ["bell pepper", "orange"])
        recommendations = self.recommendation_service.recommend(limit=1)
        inventory_names = {item.name for item in self.inventory_service.list_inventory()}

        self.assertEqual([item.ingredient_name for item in confirmation["accepted"]], ["bell pepper"])
        self.assertEqual([item.name for item in confirmation["inventory_updates"]], ["bell pepper"])
        self.assertIn("bell pepper", inventory_names)
        self.assertNotIn("orange", inventory_names)
        self.assertEqual(recommendations[0].recipe_title, "Tofu Stir Fry")


if __name__ == "__main__":
    unittest.main()
