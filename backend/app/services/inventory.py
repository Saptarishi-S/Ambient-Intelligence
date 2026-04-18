from __future__ import annotations

from backend.app.domain.models import IngredientSource, InventoryItem
from backend.app.repositories.foundation import InventoryRepository


class InventoryService:
    def __init__(self, repository: InventoryRepository) -> None:
        self.repository = repository

    def list_inventory(self):
        return self.repository.list()

    def create_item(self, payload: dict) -> InventoryItem:
        item = self._build_item(payload, default_source=IngredientSource.MANUAL.value)
        return self.repository.create(item)

    def update_item(self, item_id: int, payload: dict) -> InventoryItem:
        existing = self.repository.get(item_id)
        item = self._build_item(
            {
                "name": payload.get("name", existing.name),
                "quantity": payload.get("quantity", existing.quantity),
                "unit": payload.get("unit", existing.unit),
                "category": payload.get("category", existing.category),
                "source": payload.get("source", existing.source),
                "confidence": payload.get("confidence", existing.confidence),
            },
            default_source=existing.source,
        )
        return self.repository.update(item_id, item)

    def delete_item(self, item_id: int) -> bool:
        return self.repository.delete(item_id)

    def add_scan_items(self, items: list[InventoryItem]) -> list[InventoryItem]:
        return [self.repository.upsert_by_name(item) for item in items]

    @staticmethod
    def _build_item(payload: dict, default_source: str) -> InventoryItem:
        return InventoryItem(
            name=(payload.get("name") or "").strip().lower(),
            quantity=float(payload.get("quantity", 1)),
            unit=(payload.get("unit") or "item").strip().lower(),
            category=(payload.get("category") or "pantry").strip().lower(),
            source=(payload.get("source") or default_source).strip().lower(),
            confidence=payload.get("confidence"),
        )
