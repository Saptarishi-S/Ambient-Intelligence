from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class DietaryPreference(StrEnum):
    OMNIVORE = "omnivore"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    PESCATARIAN = "pescatarian"


class HealthGoal(StrEnum):
    WEIGHT_LOSS = "weight_loss"
    MAINTENANCE = "maintenance"
    MUSCLE_GAIN = "muscle_gain"


class IngredientSource(StrEnum):
    MANUAL = "manual"
    SCAN = "scan"


@dataclass(slots=True)
class UserProfile:
    id: int = 1
    name: str = "Demo User"
    dietary_preference: str = DietaryPreference.OMNIVORE
    allergens: list[str] = field(default_factory=list)
    health_goal: str = HealthGoal.MAINTENANCE
    calorie_target: int = 2200
    preference_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class InventoryItem:
    id: int | None = None
    name: str = ""
    quantity: float = 1.0
    unit: str = "item"
    category: str = "pantry"
    source: str = IngredientSource.MANUAL
    confidence: float | None = None
    last_updated: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class RecipeIngredient:
    name: str
    quantity: float
    unit: str
    category: str
    optional: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class Recipe:
    id: int
    title: str
    description: str
    dietary_tags: list[str]
    allergens: list[str]
    preference_tags: list[str]
    calories: int
    protein: int
    carbs: int
    fat: int
    prep_minutes: int
    instructions: list[str]
    ingredients: list[RecipeIngredient] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class RecommendationResult:
    recipe_id: int
    recipe_title: str
    score: float
    explanation: str
    ingredient_match_ratio: float = 0.0
    missing_items_ratio: float = 0.0
    health_goal_alignment: float = 0.0
    user_preference_match: float = 0.0
    calorie_fit_score: float = 0.0
    protein_fit_score: float = 0.0
    macro_balance_score: float = 0.0
    narrative_style: str = "templated"
    matched_ingredients: list[str] = field(default_factory=list)
    missing_ingredients: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class Detection:
    ingredient_name: str
    model_label: str
    confidence: float
    category: str
    quantity: float = 1.0
    unit: str = "item"
    supported: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ScanResult:
    session_id: str
    image_name: str
    detections: list[Detection]
    created_at: str
    image_mime_type: str | None = None
    image_size_bytes: int | None = None
    image_url: str | None = None
    detector: str = "mock-upload-v1"
    model_name: str | None = None
    confidence_threshold: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ShoppingListItem:
    name: str
    category: str
    quantity: float
    unit: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class DailyCalorieSummary:
    date: str
    consumed: int
    burned: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class RecommendationWeights:
    ingredient_match: float = 0.4
    missing_items: float = 0.3
    health_goal: float = 0.2
    preference_match: float = 0.1

    def to_dict(self) -> dict:
        return asdict(self)
