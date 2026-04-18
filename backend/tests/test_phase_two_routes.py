from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.api.routes import foundation as foundation_routes
from backend.app.api.routes import phase_two as phase_two_routes
from backend.app.core.database import Database
from backend.app.main import app
from backend.app.repositories.foundation import InventoryRepository, ProfileRepository, RecipeRepository, ScanRepository
from backend.app.services.detectors import YoloDetector
from backend.app.services.inventory import InventoryService
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


class PhaseTwoRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "smart_meal_planner.db")
        self.database.initialize()

        inventory_service = InventoryService(InventoryRepository(self.database))
        recommendation_service = RecommendationService(
            RecipeRepository(self.database),
            InventoryRepository(self.database),
            ProfileRepository(self.database),
        )
        self.scan_repository = ScanRepository(self.database)
        self.inventory_service = inventory_service
        self.recommendation_service = recommendation_service
        self.patches = [
            patch.object(foundation_routes, "inventory_service", inventory_service),
            patch.object(phase_two_routes, "inventory_service", inventory_service),
            patch.object(phase_two_routes, "recommendation_service", recommendation_service),
        ]
        for active_patch in self.patches:
            active_patch.start()

        self.client = TestClient(app)
        self.model_path = Path(self.temp_dir.name) / "YOLO_Model.pt"
        self.model_path.write_bytes(b"stub-model")

    def tearDown(self) -> None:
        self.client.close()
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def test_inventory_routes_round_trip_and_list_latest_state(self) -> None:
        create_response = self.client.post(
            "/inventory",
            json={"name": "Rice", "quantity": 1, "unit": "Cup", "category": "Grains"},
        )

        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()
        self.assertEqual(created["name"], "rice")
        self.assertEqual(created["unit"], "cup")
        self.assertEqual(created["category"], "grains")

        update_response = self.client.patch(
            f"/inventory/{created['id']}",
            json={"name": "Brown Rice", "quantity": 2, "category": "Pantry"},
        )

        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()
        self.assertEqual(updated["name"], "brown rice")
        self.assertEqual(updated["quantity"], 2)
        self.assertEqual(updated["category"], "pantry")

        list_response = self.client.get("/inventory")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json(), [updated])

        delete_response = self.client.delete(f"/inventory/{created['id']}")
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(self.client.get("/inventory").json(), [])

    def test_inventory_update_missing_item_returns_404(self) -> None:
        response = self.client.patch("/inventory/999", json={"quantity": 2})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Inventory item 999 not found.")

    def test_scan_upload_returns_normalized_yolo_metadata(self) -> None:
        scan_service = ScanService(
            self.scan_repository,
            self.inventory_service,
            detector=YoloDetector(
                model_path=str(self.model_path),
                confidence_threshold=0.35,
                model_loader=lambda _: StubModel(
                    [
                        StubResult(
                            names={0: "capsicum", 1: "oren", 2: "potato"},
                            boxes=[StubBox(0, 0.91), StubBox(1, 0.87), StubBox(2, 0.96)],
                        )
                    ]
                ),
            ),
        )

        with patch.object(phase_two_routes, "scan_service", scan_service):
            response = self.client.post(
                "/scan",
                files={"image": ("fridge.jpg", b"route-yolo-demo", "image/jpeg")},
                data={"image_name": "fridge.jpg"},
            )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["detector"], "yolo-ultralytics-v1")
        self.assertEqual(payload["model_name"], "YOLO_Model.pt")
        self.assertEqual(payload["confidence_threshold"], 0.35)
        self.assertEqual(
            [(item["ingredient_name"], item["model_label"], item["supported"]) for item in payload["detections"]],
            [("bell pepper", "capsicum", True), ("orange", "oren", False)],
        )


if __name__ == "__main__":
    unittest.main()
