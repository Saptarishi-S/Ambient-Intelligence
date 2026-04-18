from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import ValidationError

from backend.app.api.dependencies import calories_service, demo_data_service, inventory_service, profile_service, recommendation_service, scan_service, settings, shopping_list_service
from backend.app.api.schemas import CaloriesUpdatePayload, InventoryItemPayload, InventoryItemUpdatePayload, ProfileUpdatePayload, ScanConfirmPayload, ScanCreatePayload
from backend.app.services.detectors import DetectorInputError, DetectorRuntimeError


router = APIRouter(tags=["phase-two"])


@router.put("/profile")
def update_profile(payload: ProfileUpdatePayload) -> dict:
    return asdict(profile_service.update_profile(payload.model_dump(exclude_none=True)))


@router.post("/inventory", status_code=status.HTTP_201_CREATED)
def create_inventory_item(payload: InventoryItemPayload) -> dict:
    return asdict(inventory_service.create_item(payload.model_dump(exclude_none=True)))


@router.patch("/inventory/{item_id}")
def update_inventory_item(item_id: int, payload: InventoryItemUpdatePayload) -> dict:
    try:
        return asdict(inventory_service.update_item(item_id, payload.model_dump(exclude_none=True)))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/inventory/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(item_id: int) -> Response:
    deleted = inventory_service.delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inventory item {item_id} not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/calories/today")
def update_today_calories(payload: CaloriesUpdatePayload) -> dict:
    return asdict(calories_service.update_today_summary(payload.model_dump()))


@router.get("/recommendations")
def get_recommendations(limit: int = Query(default=3, ge=1, le=20)) -> list[dict]:
    return [asdict(item) for item in recommendation_service.recommend(limit=limit)]


@router.get("/shopping-list")
def get_shopping_list(top_n: int = Query(default=1, ge=1, le=10), recipe_ids: str | None = None) -> dict[str, list[dict]]:
    selected_ids = [int(value) for value in recipe_ids.split(",")] if recipe_ids else None
    grouped = shopping_list_service.build_list(recipe_ids=selected_ids, top_n=top_n)
    return {category: [asdict(item) for item in items] for category, items in grouped.items()}


@router.post("/scan", status_code=status.HTTP_201_CREATED)
async def create_scan(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("image")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Upload an image file in the 'image' field.")
        image_name = str(form.get("image_name") or getattr(upload, "filename", "") or "fridge-upload")
        image_bytes = await upload.read()
        if not image_bytes:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uploaded image is empty.")
        if len(image_bytes) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Uploaded image exceeds the {settings.max_upload_size_bytes} byte limit.",
            )
        try:
            return asdict(scan_service.scan_upload(image_name=image_name, image_bytes=image_bytes, image_mime_type=getattr(upload, "content_type", None)))
        except DetectorInputError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except DetectorRuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    try:
        payload = ScanCreatePayload.model_validate(await request.json())
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    try:
        return asdict(scan_service.scan_image(payload.image_name))
    except DetectorInputError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except DetectorRuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/scan/{session_id}")
def get_scan(session_id: str) -> dict:
    try:
        return asdict(scan_service.get_scan(session_id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/scan/{session_id}/image")
def get_scan_image(session_id: str):
    try:
        image_path = scan_service.get_image_path(session_id)
        scan_result = scan_service.get_scan(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FileResponse(path=image_path, media_type=scan_result.image_mime_type or "application/octet-stream", filename=scan_result.image_name)


@router.post("/scan/confirm")
def confirm_scan(session_id: str, payload: ScanConfirmPayload) -> dict:
    try:
        result = scan_service.confirm_scan(session_id, payload.accepted_ingredients)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {
        "scan_result": asdict(result["scan_result"]),
        "accepted": [asdict(item) for item in result["accepted"]],
        "inventory_updates": [asdict(item) for item in result["inventory_updates"]],
    }


@router.get("/demo/scenarios")
def list_demo_scenarios() -> list[dict]:
    return demo_data_service.list_scenarios()


@router.post("/demo/reset")
def reset_demo_state() -> dict:
    return demo_data_service.reset_demo()


@router.post("/demo/load/{scenario_id}")
def load_demo_scenario(scenario_id: str) -> dict:
    try:
        return demo_data_service.load_scenario(scenario_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
