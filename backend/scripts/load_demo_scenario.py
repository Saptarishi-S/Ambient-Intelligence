from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.api.dependencies import demo_data_service  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python backend/scripts/load_demo_scenario.py <scenario_id>")
        return 1

    scenario_id = sys.argv[1]
    try:
        snapshot = demo_data_service.load_scenario(scenario_id)
    except LookupError as exc:
        print(str(exc))
        return 2

    print(json.dumps(snapshot, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

