from __future__ import annotations

from backend.app.core.database import create_database
from backend.app.core.settings import get_settings
from backend.app.repositories.foundation import CaloriesRepository, InventoryRepository, MetadataRepository, ProfileRepository, RecipeRepository, ScanRepository
from backend.app.services.calories import CaloriesService
from backend.app.services.demo import DemoDataService
from backend.app.services.detectors import bootstrap_detector
from backend.app.services.inventory import InventoryService
from backend.app.services.profile import ProfileService
from backend.app.services.recipes import RecipeService
from backend.app.services.recommendations import RecommendationService
from backend.app.services.scans import ScanService
from backend.app.services.shopping import ShoppingListService


settings = get_settings()
database = create_database()

profile_repository = ProfileRepository(database)
inventory_repository = InventoryRepository(database)
recipe_repository = RecipeRepository(database)
metadata_repository = MetadataRepository(database)
calories_repository = CaloriesRepository(database)
scan_repository = ScanRepository(database)

detector_bootstrap = bootstrap_detector(settings.detector_mode)
detector = detector_bootstrap.detector

profile_service = ProfileService(profile_repository)
inventory_service = InventoryService(inventory_repository)
recipe_service = RecipeService(recipe_repository, metadata_repository)
calories_service = CaloriesService(calories_repository)
recommendation_service = RecommendationService(recipe_repository, inventory_repository, profile_repository)
scan_service = ScanService(scan_repository, inventory_service, detector=detector)
shopping_list_service = ShoppingListService(recipe_repository, recommendation_service)
demo_data_service = DemoDataService(profile_repository, inventory_repository, calories_repository, recommendation_service)


def get_detector_runtime_status() -> dict[str, str | None]:
    return {
        "detector_requested": detector_bootstrap.requested_mode,
        "detector_active": detector_bootstrap.active_mode,
        "detector_warning": detector_bootstrap.warning,
    }
