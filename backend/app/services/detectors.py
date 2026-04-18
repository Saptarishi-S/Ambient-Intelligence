from __future__ import annotations

import importlib.util
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from backend.app.domain.models import Detection


class DetectorConfigurationError(RuntimeError):
    pass


class DetectorInputError(ValueError):
    pass


class DetectorRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DetectorBootstrapResult:
    detector: "DetectorInterface"
    requested_mode: str
    active_mode: str
    warning: str | None = None


@dataclass(frozen=True, slots=True)
class LabelNormalization:
    ingredient_name: str
    category: str
    quantity: float
    unit: str
    supported: bool


def _clean_model_label(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


YOLO_LABEL_REGISTRY: dict[str, LabelNormalization] = {
    "apple": LabelNormalization("apple", "produce", 1, "item", False),
    "banana": LabelNormalization("banana", "produce", 1, "item", False),
    "capsicum": LabelNormalization("bell pepper", "produce", 1, "item", True),
    "cucumber": LabelNormalization("cucumber", "produce", 1, "item", True),
    "dragon fruit": LabelNormalization("dragon fruit", "produce", 1, "item", False),
    "guava": LabelNormalization("guava", "produce", 1, "item", False),
    "orange": LabelNormalization("orange", "produce", 1, "item", False),
    "oren": LabelNormalization("orange", "produce", 1, "item", False),
    "pear": LabelNormalization("pear", "produce", 1, "item", False),
    "pineapple": LabelNormalization("pineapple", "produce", 1, "item", False),
    "sugar apple": LabelNormalization("sugar apple", "produce", 1, "item", False),
    "tomato": LabelNormalization("tomato", "produce", 1, "item", True),
}

IGNORED_YOLO_LABELS = {
    "bitter melon",
    "brinjal",
    "cabbage",
    "calabash",
    "cauliflower",
    "garlic",
    "ginger",
    "green chili",
    "lady finger",
    "onion",
    "potato",
    "sponge gourd",
}


def normalize_yolo_label(model_label: str) -> LabelNormalization | None:
    cleaned = _clean_model_label(model_label)
    if not cleaned or cleaned in IGNORED_YOLO_LABELS:
        return None
    return YOLO_LABEL_REGISTRY.get(cleaned)


def _normalized_detector_mode(value: str | None) -> str:
    return (value or "mock").strip().lower() or "mock"


class DetectorInterface:
    detector_name = "base"
    model_name: str | None = None
    confidence_threshold: float | None = None

    def detect(self, image_name: str, image_bytes: bytes | None = None) -> list[Detection]:
        raise NotImplementedError


class MockDetector(DetectorInterface):
    detector_name = "mock-upload-v2"

    def detect(self, image_name: str, image_bytes: bytes | None = None) -> list[Detection]:
        lookup = {
            "breakfast": [
                Detection(ingredient_name="egg", model_label="egg", confidence=0.96, category="protein", quantity=4, unit="item"),
                Detection(ingredient_name="spinach", model_label="spinach", confidence=0.88, category="produce", quantity=1, unit="cup"),
                Detection(ingredient_name="cheese", model_label="cheese", confidence=0.84, category="dairy", quantity=0.5, unit="cup"),
            ],
            "veggie": [
                Detection(ingredient_name="broccoli", model_label="broccoli", confidence=0.94, category="produce", quantity=1, unit="cup"),
                Detection(ingredient_name="bell pepper", model_label="bell pepper", confidence=0.9, category="produce", quantity=1, unit="item"),
                Detection(ingredient_name="tofu", model_label="tofu", confidence=0.91, category="protein", quantity=200, unit="g"),
            ],
            "protein": [
                Detection(ingredient_name="chicken breast", model_label="chicken breast", confidence=0.95, category="protein", quantity=200, unit="g"),
                Detection(ingredient_name="rice", model_label="rice", confidence=0.86, category="grains", quantity=1, unit="cup"),
                Detection(ingredient_name="broccoli", model_label="broccoli", confidence=0.82, category="produce", quantity=1, unit="cup"),
            ],
        }
        normalized = image_name.lower()
        for key, detections in lookup.items():
            if key in normalized:
                return detections

        if image_bytes:
            signal = sum(image_bytes[:32]) % 3
            upload_lookup = {
                0: [
                    Detection(ingredient_name="tomato", model_label="tomato", confidence=0.83, category="produce", quantity=2, unit="item"),
                    Detection(ingredient_name="cucumber", model_label="cucumber", confidence=0.79, category="produce", quantity=1, unit="item"),
                    Detection(ingredient_name="milk", model_label="milk", confidence=0.72, category="dairy", quantity=1, unit="bottle"),
                ],
                1: [
                    Detection(ingredient_name="egg", model_label="egg", confidence=0.9, category="protein", quantity=4, unit="item"),
                    Detection(ingredient_name="spinach", model_label="spinach", confidence=0.81, category="produce", quantity=1, unit="cup"),
                    Detection(ingredient_name="greek yogurt", model_label="greek yogurt", confidence=0.75, category="dairy", quantity=1, unit="cup"),
                ],
                2: [
                    Detection(ingredient_name="broccoli", model_label="broccoli", confidence=0.85, category="produce", quantity=1, unit="cup"),
                    Detection(ingredient_name="rice", model_label="rice", confidence=0.8, category="grains", quantity=1, unit="cup"),
                    Detection(ingredient_name="chicken breast", model_label="chicken breast", confidence=0.78, category="protein", quantity=200, unit="g"),
                ],
            }
            return upload_lookup[signal]

        return [
            Detection(ingredient_name="milk", model_label="milk", confidence=0.72, category="dairy", quantity=1, unit="bottle"),
            Detection(ingredient_name="tomato", model_label="tomato", confidence=0.83, category="produce", quantity=2, unit="item"),
            Detection(ingredient_name="cucumber", model_label="cucumber", confidence=0.79, category="produce", quantity=1, unit="item"),
        ]


class YoloDetector(DetectorInterface):
    detector_name = "yolo-ultralytics-v1"

    def __init__(
        self,
        model_path: str | None = None,
        confidence_threshold: float | None = None,
        model_loader=None,
    ) -> None:
        configured_model_path = (model_path or os.getenv("SMART_MEAL_PLANNER_YOLO_MODEL", "")).strip()
        if not configured_model_path:
            raise DetectorConfigurationError(
                "YOLO detector is enabled but SMART_MEAL_PLANNER_YOLO_MODEL is not configured."
            )

        self.model_path = Path(configured_model_path).expanduser()
        if not self.model_path.is_file():
            raise DetectorConfigurationError(
                f"YOLO detector is enabled but the model weights were not found at '{self.model_path}'."
            )

        raw_confidence = confidence_threshold
        if raw_confidence is None:
            raw_confidence = float(os.getenv("SMART_MEAL_PLANNER_YOLO_CONFIDENCE", "0.35"))
        if not 0 <= float(raw_confidence) <= 1:
            raise DetectorConfigurationError(
                "SMART_MEAL_PLANNER_YOLO_CONFIDENCE must be between 0 and 1."
            )

        self.confidence_threshold = float(raw_confidence)
        self.model_name = self.model_path.name
        self._model = self._load_model(model_loader)

    def detect(self, image_name: str, image_bytes: bytes | None = None) -> list[Detection]:
        if not image_bytes:
            raise DetectorInputError(
                "YOLO mode requires an uploaded fridge image. Switch SMART_MEAL_PLANNER_DETECTOR=mock to use sample-name scans."
            )

        suffix = Path(image_name).suffix or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="smart-meal-yolo-") as temp_file:
            temp_file.write(image_bytes)
            temp_path = Path(temp_file.name)
        try:
            results = self._model.predict(
                source=str(temp_path),
                verbose=False,
                conf=self.confidence_threshold,
            )
        except Exception as exc:
            raise DetectorRuntimeError(f"YOLO inference failed while scanning '{image_name}'.") from exc
        finally:
            temp_path.unlink(missing_ok=True)

        detections: list[Detection] = []
        for result in results:
            names = getattr(result, "names", {})
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                class_id = int(self._scalar_value(getattr(box, "cls", 0)))
                confidence = float(self._scalar_value(getattr(box, "conf", 0.0)))
                if confidence < self.confidence_threshold:
                    continue
                model_label = _clean_model_label(str(names.get(class_id, "")))
                normalized = normalize_yolo_label(model_label)
                if normalized is None:
                    continue
                detections.append(
                    Detection(
                        ingredient_name=normalized.ingredient_name,
                        model_label=model_label,
                        confidence=round(confidence, 4),
                        category=normalized.category,
                        quantity=normalized.quantity,
                        unit=normalized.unit,
                        supported=normalized.supported,
                    )
                )

        return detections

    def _load_model(self, model_loader):
        if model_loader is not None:
            return model_loader(self.model_path)

        missing_modules = [
            module_name
            for module_name in ("torch", "ultralytics")
            if importlib.util.find_spec(module_name) is None
        ]
        if missing_modules:
            missing_runtime = ", ".join(missing_modules)
            raise DetectorConfigurationError(
                f"YOLO detector is enabled but the runtime is missing ({missing_runtime}). "
                "Recreate the backend virtual environment on a YOLO-compatible Python version, "
                "reinstall backend requirements, and try again."
            )

        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError as exc:
            raise DetectorConfigurationError(
                "YOLO detector is enabled but the ultralytics runtime could not be imported."
            ) from exc

        try:
            return YOLO(str(self.model_path))
        except Exception as exc:
            raise DetectorConfigurationError(
                f"Failed to load YOLO weights from '{self.model_path}'."
            ) from exc

    @classmethod
    def _scalar_value(cls, value: object) -> float:
        if isinstance(value, (list, tuple)):
            if not value:
                return 0.0
            return cls._scalar_value(value[0])
        if hasattr(value, "tolist"):
            listed = value.tolist()
            if isinstance(listed, list):
                if not listed:
                    return 0.0
                return cls._scalar_value(listed[0])
            return float(listed)
        if hasattr(value, "item"):
            return float(value.item())
        return float(value)


def bootstrap_detector(detector_mode: str | None = None) -> DetectorBootstrapResult:
    requested_mode = _normalized_detector_mode(detector_mode or os.getenv("SMART_MEAL_PLANNER_DETECTOR"))

    if requested_mode == "mock":
        return DetectorBootstrapResult(
            detector=MockDetector(),
            requested_mode="mock",
            active_mode="mock",
        )

    if requested_mode == "yolo":
        try:
            detector = YoloDetector()
        except DetectorConfigurationError as exc:
            return DetectorBootstrapResult(
                detector=MockDetector(),
                requested_mode="yolo",
                active_mode="mock",
                warning=str(exc),
            )
        return DetectorBootstrapResult(
            detector=detector,
            requested_mode="yolo",
            active_mode="yolo",
        )

    return DetectorBootstrapResult(
        detector=MockDetector(),
        requested_mode=requested_mode,
        active_mode="mock",
        warning=(
            f"Unsupported SMART_MEAL_PLANNER_DETECTOR value '{requested_mode}'. "
            "Falling back to mock mode."
        ),
    )


def build_detector(detector_mode: str | None = None) -> DetectorInterface:
    return bootstrap_detector(detector_mode).detector
