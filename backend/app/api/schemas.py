from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileUpdatePayload(BaseModel):
    name: str | None = None
    dietary_preference: str | None = None
    allergens: list[str] | None = None
    health_goal: str | None = None
    calorie_target: int | None = Field(default=None, ge=0)
    preference_tags: list[str] | None = None


class InventoryItemPayload(BaseModel):
    name: str
    quantity: float = Field(default=1, gt=0)
    unit: str = "item"
    category: str = "pantry"
    source: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class InventoryItemUpdatePayload(BaseModel):
    name: str | None = None
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = None
    category: str | None = None
    source: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class CaloriesUpdatePayload(BaseModel):
    consumed: int = Field(ge=0)
    burned: int = Field(ge=0)


class ScanCreatePayload(BaseModel):
    image_name: str = Field(min_length=1)


class ScanConfirmPayload(BaseModel):
    accepted_ingredients: list[str] | None = None
