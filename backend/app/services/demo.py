from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from backend.app.core.seed import DEFAULT_PROFILE
from backend.app.domain.models import IngredientSource, InventoryItem, UserProfile
from backend.app.repositories.foundation import CaloriesRepository, InventoryRepository, ProfileRepository
from backend.app.services.recommendations import RecommendationService


DEFAULT_CALORIES = {"consumed": 1450, "burned": 520}


class DemoDataService:
    def __init__(
        self,
        profile_repository: ProfileRepository,
        inventory_repository: InventoryRepository,
        calories_repository: CaloriesRepository,
        recommendation_service: RecommendationService,
        scenarios_path: Path | None = None,
    ) -> None:
        self.profile_repository = profile_repository
        self.inventory_repository = inventory_repository
        self.calories_repository = calories_repository
        self.recommendation_service = recommendation_service
        self.scenarios_path = scenarios_path or Path(__file__).resolve().parents[2] / "demo" / "scenarios.json"

    def list_scenarios(self) -> list[dict]:
        scenarios = self._load_scenarios()
        return [
            {"id": scenario["id"], "name": scenario["name"], "description": scenario["description"]}
            for scenario in scenarios
        ]

    def reset_demo(self) -> dict:
        profile = UserProfile(
            id=1,
            name=DEFAULT_PROFILE["name"],
            dietary_preference=DEFAULT_PROFILE["dietary_preference"],
            allergens=list(DEFAULT_PROFILE["allergens"]),
            health_goal=DEFAULT_PROFILE["health_goal"],
            calorie_target=DEFAULT_PROFILE["calorie_target"],
            preference_tags=list(DEFAULT_PROFILE["preference_tags"]),
        )
        self.profile_repository.reset(profile)
        self.inventory_repository.replace_all([])
        self.calories_repository.reset_today(
            consumed=DEFAULT_CALORIES["consumed"],
            burned=DEFAULT_CALORIES["burned"],
        )
        return self._snapshot()

    def load_scenario(self, scenario_id: str) -> dict:
        scenario = next((item for item in self._load_scenarios() if item["id"] == scenario_id), None)
        if scenario is None:
            raise LookupError(f"Demo scenario '{scenario_id}' not found.")

        profile_payload = scenario["profile"]
        profile = UserProfile(
            id=1,
            name=profile_payload["name"],
            dietary_preference=profile_payload["dietary_preference"],
            allergens=list(profile_payload["allergens"]),
            health_goal=profile_payload["health_goal"],
            calorie_target=int(profile_payload["calorie_target"]),
            preference_tags=list(profile_payload["preference_tags"]),
        )
        inventory_items = [
            InventoryItem(
                name=item["name"],
                quantity=float(item["quantity"]),
                unit=item["unit"],
                category=item["category"],
                source=IngredientSource.MANUAL.value,
                confidence=None,
            )
            for item in scenario["inventory"]
        ]

        self.profile_repository.reset(profile)
        self.inventory_repository.replace_all(inventory_items)
        self.calories_repository.reset_today(
            consumed=int(scenario["calories"]["consumed"]),
            burned=int(scenario["calories"]["burned"]),
        )
        snapshot = self._snapshot()
        snapshot["active_scenario"] = {
            "id": scenario["id"],
            "name": scenario["name"],
            "description": scenario["description"],
        }
        return snapshot

    def _snapshot(self) -> dict:
        profile = self.profile_repository.get()
        inventory = self.inventory_repository.list()
        calories = self.calories_repository.get_today()
        recommendations = self.recommendation_service.recommend(limit=3)
        return {
            "profile": asdict(profile),
            "inventory": [asdict(item) for item in inventory],
            "calories": asdict(calories),
            "recommendations": [asdict(item) for item in recommendations],
        }

    def _load_scenarios(self) -> list[dict]:
        return json.loads(self.scenarios_path.read_text(encoding="utf-8"))
