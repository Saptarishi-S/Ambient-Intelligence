from __future__ import annotations

from pathlib import Path

from backend.app.core.storage import build_upload_path
from backend.app.domain.models import IngredientSource, InventoryItem
from backend.app.repositories.foundation import ScanRepository
from backend.app.services.detectors import DetectorInterface, MockDetector
from backend.app.services.inventory import InventoryService


class ScanService:
    def __init__(
        self,
        repository: ScanRepository,
        inventory_service: InventoryService,
        detector: DetectorInterface | None = None,
    ) -> None:
        self.repository = repository
        self.inventory_service = inventory_service
        self.detector = detector or MockDetector()

    def scan_image(self, image_name: str):
        detections = self.detector.detect(image_name=image_name)
        result = self.repository.create(
            image_name=image_name,
            detections=detections,
            detector=self.detector.detector_name,
            model_name=self.detector.model_name,
            confidence_threshold=self.detector.confidence_threshold,
        )
        return self._attach_image_url(result)

    def scan_upload(self, image_name: str, image_bytes: bytes, image_mime_type: str | None = None):
        upload_path = build_upload_path(image_name)
        upload_path.write_bytes(image_bytes)
        detections = self.detector.detect(image_name=image_name, image_bytes=image_bytes)
        result = self.repository.create(
            image_name=image_name,
            detections=detections,
            image_mime_type=image_mime_type,
            image_size_bytes=len(image_bytes),
            stored_image_path=str(upload_path),
            detector=self.detector.detector_name,
            model_name=self.detector.model_name,
            confidence_threshold=self.detector.confidence_threshold,
        )
        return self._attach_image_url(result)

    def get_scan(self, session_id: str):
        return self._attach_image_url(self.repository.get(session_id))

    def confirm_scan(self, session_id: str, accepted_ingredients: list[str] | None = None):
        scan_result = self.get_scan(session_id)
        accepted = None if accepted_ingredients is None else {name.strip().lower() for name in accepted_ingredients}
        accepted_detections = []
        for detection in scan_result.detections:
            if not detection.supported:
                continue
            if accepted is not None and detection.ingredient_name.lower() not in accepted:
                continue
            accepted_detections.append(detection)

        inventory_items = [
            InventoryItem(
                name=detection.ingredient_name.lower(),
                quantity=detection.quantity,
                unit=detection.unit,
                category=detection.category,
                source=IngredientSource.SCAN.value,
                confidence=detection.confidence,
            )
            for detection in accepted_detections
        ]
        updated_inventory = self.inventory_service.add_scan_items(inventory_items)
        return {"scan_result": scan_result, "accepted": accepted_detections, "inventory_updates": updated_inventory}

    @staticmethod
    def _attach_image_url(scan_result):
        if scan_result.image_url:
            scan_result.image_url = f"/scan/{scan_result.session_id}/image"
        return scan_result

    def get_image_path(self, session_id: str) -> Path:
        scan_result = self.repository.get(session_id)
        if not scan_result.image_url:
            raise LookupError(f"Scan session {session_id} does not have an uploaded image.")
        return Path(scan_result.image_url)
