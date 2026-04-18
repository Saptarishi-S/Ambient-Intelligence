from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.core.settings import get_settings
from backend.app.main import app


class ConnectivityBootstrapTests(unittest.TestCase):
    def test_get_settings_reads_backend_env_file_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("backend.app.core.settings.Path.is_file", return_value=True), patch(
                "backend.app.core.settings.Path.read_text",
                return_value="\n".join(
                    [
                        "SMART_MEAL_PLANNER_DETECTOR=yolo",
                        "SMART_MEAL_PLANNER_YOLO_MODEL=D:\\Ambient\\Ambient\\YOLO_Model.pt",
                        "SMART_MEAL_PLANNER_YOLO_CONFIDENCE=0.42",
                    ]
                ),
            ):
                settings = get_settings()

        self.assertEqual(settings.detector_mode, "yolo")
        self.assertEqual(settings.yolo_model_path, "D:\\Ambient\\Ambient\\YOLO_Model.pt")
        self.assertEqual(settings.yolo_confidence, 0.42)

    def test_health_endpoint_returns_detector_diagnostics(self) -> None:
        with TestClient(app) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("detector_requested", payload)
        self.assertIn("detector_active", payload)
        self.assertIn("detector_warning", payload)
        self.assertIn("max_upload_size_bytes", payload)


if __name__ == "__main__":
    unittest.main()
