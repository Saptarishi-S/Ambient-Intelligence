from __future__ import annotations

from backend.app.domain.models import RecommendationResult, RecommendationWeights
from backend.app.repositories.foundation import InventoryRepository, ProfileRepository, RecipeRepository


class RecommendationService:
    def __init__(
        self,
        recipe_repository: RecipeRepository,
        inventory_repository: InventoryRepository,
        profile_repository: ProfileRepository,
    ) -> None:
        self.recipe_repository = recipe_repository
        self.inventory_repository = inventory_repository
        self.profile_repository = profile_repository
        self.weights = RecommendationWeights()

    def recommend(self, limit: int = 3) -> list[RecommendationResult]:
        profile = self.profile_repository.get()
        inventory_items = self.inventory_repository.list()
        inventory_names = {item.name.strip().lower() for item in inventory_items}
        recipes = self.recipe_repository.list()

        valid_recipes = [recipe for recipe in recipes if self._is_recipe_compatible(recipe, profile)]
        recommendations = [self._score_recipe(recipe, profile, inventory_names) for recipe in valid_recipes]
        recommendations.sort(key=lambda item: item.score, reverse=True)
        return recommendations[:limit]

    def _is_recipe_compatible(self, recipe, profile) -> bool:
        allowed_tags = self._allowed_dietary_tags(profile.dietary_preference)
        if recipe.dietary_tags and not any(tag in allowed_tags for tag in recipe.dietary_tags):
            return False
        if set(profile.allergens).intersection({allergen.lower() for allergen in recipe.allergens}):
            return False
        return True

    def _score_recipe(self, recipe, profile, inventory_names: set[str]) -> RecommendationResult:
        required_ingredients = [ingredient for ingredient in recipe.ingredients if not ingredient.optional]
        matched = [ingredient.name for ingredient in required_ingredients if ingredient.name.lower() in inventory_names]
        missing = [ingredient.name for ingredient in required_ingredients if ingredient.name.lower() not in inventory_names]
        total_required = max(len(required_ingredients), 1)
        ingredient_match_ratio = len(matched) / total_required
        missing_items_ratio = len(missing) / total_required
        nutrition_scores = self._nutrition_scores(recipe, profile.health_goal, profile.calorie_target)
        health_goal_alignment = nutrition_scores["health_goal_alignment"]
        user_preference_match = self._preference_score(recipe.preference_tags, profile.preference_tags)
        score = (
            self.weights.ingredient_match * ingredient_match_ratio
            + self.weights.missing_items * (1 - missing_items_ratio)
            + self.weights.health_goal * health_goal_alignment
            + self.weights.preference_match * user_preference_match
        )

        explanation = self._build_explanation(
            recipe=recipe,
            profile=profile,
            matched=matched,
            missing=missing,
            total_required=total_required,
            nutrition_scores=nutrition_scores,
        )
        return RecommendationResult(
            recipe_id=recipe.id,
            recipe_title=recipe.title,
            score=round(score, 4),
            explanation=explanation,
            ingredient_match_ratio=round(ingredient_match_ratio, 4),
            missing_items_ratio=round(missing_items_ratio, 4),
            health_goal_alignment=round(health_goal_alignment, 4),
            user_preference_match=round(user_preference_match, 4),
            calorie_fit_score=round(nutrition_scores["calorie_fit_score"], 4),
            protein_fit_score=round(nutrition_scores["protein_fit_score"], 4),
            macro_balance_score=round(nutrition_scores["macro_balance_score"], 4),
            narrative_style="templated-nlg-v1",
            matched_ingredients=matched,
            missing_ingredients=missing,
        )

    @staticmethod
    def _allowed_dietary_tags(dietary_preference: str) -> set[str]:
        compatibility = {
            "omnivore": {"omnivore", "vegetarian", "vegan", "pescatarian"},
            "vegetarian": {"vegetarian", "vegan"},
            "vegan": {"vegan"},
            "pescatarian": {"pescatarian", "vegetarian", "vegan"},
        }
        return compatibility.get(dietary_preference, {dietary_preference})

    @staticmethod
    def _nutrition_scores(recipe, health_goal: str, calorie_target: int) -> dict[str, float]:
        meal_target = max(calorie_target / 3, 1)
        calorie_distance = abs(recipe.calories - meal_target)
        calorie_fit = max(0.0, min(1.0, 1 - (calorie_distance / meal_target)))
        protein_fit = max(0.0, min(1.0, recipe.protein / 40))
        macro_balance = RecommendationService._macro_balance_score(recipe.protein, recipe.carbs, recipe.fat)

        if health_goal == "weight_loss":
            health_alignment = (0.55 * calorie_fit) + (0.25 * macro_balance) + (0.20 * protein_fit)
        elif health_goal == "muscle_gain":
            calorie_support = max(0.0, min(1.0, recipe.calories / max(meal_target, 1)))
            health_alignment = (0.5 * protein_fit) + (0.3 * macro_balance) + (0.2 * calorie_support)
        else:
            health_alignment = (0.45 * calorie_fit) + (0.3 * macro_balance) + (0.25 * protein_fit)

        return {
            "health_goal_alignment": max(0.0, min(1.0, health_alignment)),
            "calorie_fit_score": calorie_fit,
            "protein_fit_score": protein_fit,
            "macro_balance_score": macro_balance,
        }

    @staticmethod
    def _preference_score(recipe_tags: list[str], user_tags: list[str]) -> float:
        if not user_tags:
            return 0.5
        overlap = len(set(recipe_tags).intersection(set(user_tags)))
        return overlap / len(user_tags)

    @staticmethod
    def _macro_balance_score(protein: int, carbs: int, fat: int) -> float:
        total_macro_calories = max((protein * 4) + (carbs * 4) + (fat * 9), 1)
        protein_share = (protein * 4) / total_macro_calories
        carbs_share = (carbs * 4) / total_macro_calories
        fat_share = (fat * 9) / total_macro_calories
        ideal = {"protein": 0.3, "carbs": 0.4, "fat": 0.3}
        deviation = (
            abs(protein_share - ideal["protein"])
            + abs(carbs_share - ideal["carbs"])
            + abs(fat_share - ideal["fat"])
        )
        return max(0.0, min(1.0, 1 - deviation))

    @staticmethod
    def _build_explanation(recipe, profile, matched: list[str], missing: list[str], total_required: int, nutrition_scores: dict[str, float]) -> str:
        match_sentence = f"It already covers {len(matched)} of {total_required} required ingredients"
        if missing:
            match_sentence += f" and only needs {len(missing)} more: {', '.join(missing)}."
        else:
            match_sentence += " and does not require extra shopping."

        goal_phrase = {
            "weight_loss": "keeps calories comparatively controlled",
            "muscle_gain": "leans into higher protein support",
            "maintenance": "lands near a balanced everyday target",
        }.get(profile.health_goal, "matches your goal profile")
        nutrition_sentence = (
            f"Nutritionally, it {goal_phrase} with calorie fit at {nutrition_scores['calorie_fit_score']:.0%}, "
            f"protein fit at {nutrition_scores['protein_fit_score']:.0%}, and macro balance at {nutrition_scores['macro_balance_score']:.0%}."
        )
        preference_sentence = f"It also reflects recipe tags like {', '.join(recipe.preference_tags[:3]) or 'general meal planning'}."
        return f"{match_sentence} {nutrition_sentence} {preference_sentence}"
