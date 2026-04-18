from __future__ import annotations

from backend.app.domain.models import ShoppingListItem
from backend.app.repositories.foundation import RecipeRepository
from backend.app.services.recommendations import RecommendationService


class ShoppingListService:
    def __init__(self, recipe_repository: RecipeRepository, recommendation_service: RecommendationService) -> None:
        self.recipe_repository = recipe_repository
        self.recommendation_service = recommendation_service

    def build_list(self, recipe_ids: list[int] | None = None, top_n: int = 1) -> dict[str, list[ShoppingListItem]]:
        if recipe_ids:
            selected_ids = set(recipe_ids)
        else:
            selected_ids = {recommendation.recipe_id for recommendation in self.recommendation_service.recommend(limit=top_n)}

        recipes = [recipe for recipe in self.recipe_repository.list() if recipe.id in selected_ids]
        grouped: dict[str, dict[str, ShoppingListItem]] = {}
        recommendation_limit = max(len(self.recipe_repository.list()), top_n, len(selected_ids) or 1)
        recommendations = {item.recipe_id: item for item in self.recommendation_service.recommend(limit=recommendation_limit)}

        for recipe in recipes:
            recommendation = recommendations.get(recipe.id)
            missing_names = set(recommendation.missing_ingredients if recommendation else [])
            for ingredient in recipe.ingredients:
                if ingredient.name not in missing_names:
                    continue
                category_bucket = grouped.setdefault(ingredient.category, {})
                existing = category_bucket.get(ingredient.name)
                if existing is None:
                    category_bucket[ingredient.name] = ShoppingListItem(
                        name=ingredient.name,
                        category=ingredient.category,
                        quantity=ingredient.quantity,
                        unit=ingredient.unit,
                    )
                else:
                    existing.quantity += ingredient.quantity

        return {category: sorted(items.values(), key=lambda item: item.name) for category, items in grouped.items()}
