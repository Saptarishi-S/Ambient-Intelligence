from __future__ import annotations

from backend.app.repositories.foundation import CaloriesRepository


class CaloriesService:
    def __init__(self, repository: CaloriesRepository) -> None:
        self.repository = repository

    def get_today_summary(self):
        return self.repository.get_today()

    def update_today_summary(self, payload: dict):
        consumed = int(payload.get("consumed", 0))
        burned = int(payload.get("burned", 0))
        return self.repository.update_today(consumed=consumed, burned=burned)
