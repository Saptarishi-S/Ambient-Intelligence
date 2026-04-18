from __future__ import annotations

from backend.app.domain.models import UserProfile
from backend.app.repositories.foundation import ProfileRepository


class ProfileService:
    def __init__(self, repository: ProfileRepository) -> None:
        self.repository = repository

    def get_profile(self):
        return self.repository.get()

    def update_profile(self, payload: dict) -> UserProfile:
        current = self.repository.get()
        profile = UserProfile(
            id=current.id,
            name=(payload.get("name") or current.name).strip(),
            dietary_preference=payload.get("dietary_preference", current.dietary_preference),
            allergens=self._normalize_tags(payload.get("allergens", current.allergens)),
            health_goal=payload.get("health_goal", current.health_goal),
            calorie_target=int(payload.get("calorie_target", current.calorie_target)),
            preference_tags=self._normalize_tags(payload.get("preference_tags", current.preference_tags)),
        )
        return self.repository.update(profile)

    @staticmethod
    def _normalize_tags(values: list[str]) -> list[str]:
        normalized = {value.strip().lower() for value in values if value and value.strip()}
        return sorted(normalized)
