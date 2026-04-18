from __future__ import annotations

from backend.app.repositories.foundation import MetadataRepository, RecipeRepository


class RecipeService:
    def __init__(self, recipe_repository: RecipeRepository, metadata_repository: MetadataRepository) -> None:
        self.recipe_repository = recipe_repository
        self.metadata_repository = metadata_repository

    def list_recipes(self):
        return self.recipe_repository.list()

    def get_reference_data(self):
        return self.metadata_repository.get_all()

