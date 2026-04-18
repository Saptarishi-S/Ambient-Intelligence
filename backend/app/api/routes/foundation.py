from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from backend.app.api.dependencies import calories_service, inventory_service, profile_service, recipe_service


router = APIRouter(tags=["foundation"])


@router.get("/profile")
def get_profile() -> dict:
    return asdict(profile_service.get_profile())


@router.get("/inventory")
def list_inventory() -> list[dict]:
    return [asdict(item) for item in inventory_service.list_inventory()]


@router.get("/recipes")
def list_recipes() -> list[dict]:
    return [asdict(recipe) for recipe in recipe_service.list_recipes()]


@router.get("/metadata")
def get_metadata() -> dict[str, list[dict[str, str | int]]]:
    return recipe_service.get_reference_data()


@router.get("/calories/today")
def get_today_calories() -> dict:
    return asdict(calories_service.get_today_summary())

