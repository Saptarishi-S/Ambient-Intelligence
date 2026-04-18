# Smart Meal Planner

Phase 1 through Phase 5 foundation for the Smart Meal Planner project.

## What is included

- FastAPI-ready backend structure
- Shared domain models for profile, inventory, recipes, scans, shopping lists, recommendations, and calories
- SQLite bootstrap and seed data
- Working backend services for profile updates, inventory CRUD, macro-aware recipe scoring, shopping lists, and upload-aware fridge scans
- Detector abstraction with a default mock detector and a real YOLO-backed upload path for fridge scan review
- API endpoints for health, profile, inventory, recipes, metadata, scans, scan-image preview, recommendations, shopping lists, and today's calorie summary
- Next.js frontend dashboard for profile editing, calorie tracking, inventory management, scan review, recommendations, and shopping lists
- Demo scenario endpoints and local reset/load scripts for repeatable walkthroughs
- Standard-library tests for the seed/bootstrap layer

## Project structure

```text
backend/
  .env.example
  app/
    api/
    core/
    domain/
    repositories/
    services/
  demo/
  scripts/
  tests/
frontend/
  app/
  components/
  lib/
```

## Backend setup

1. Create a virtual environment.
2. Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

Optional backend environment variables are documented in [backend/.env.example](D:\Ambient Intelligence\backend\.env.example). The backend auto-loads [backend/.env](D:\Ambient Intelligence\backend\.env) when that file exists, and the launcher now creates it from the example file if needed.

3. Run the API:

```bash
uvicorn backend.app.main:app --reload
```

The SQLite database is created under your system temp directory by default in this scaffold. To choose a persistent location, set `SMART_MEAL_PLANNER_DB_PATH`.
To experiment with detector backends, use `SMART_MEAL_PLANNER_DETECTOR=mock` or `SMART_MEAL_PLANNER_DETECTOR=yolo`.

YOLO mode now expects the runtime and weights to be configured up front:

- `SMART_MEAL_PLANNER_YOLO_MODEL` should point at the external weights file, for example `D:\Ambient\Ambient\YOLO_Model.pt`
- `SMART_MEAL_PLANNER_YOLO_CONFIDENCE` defaults to `0.35`
- the backend virtual environment must be recreated on a Python release below `3.14` before installing `backend/requirements.txt`, otherwise `torch` and `ultralytics` will be skipped

If YOLO is misconfigured or its runtime is missing, the backend now stays up, reports the warning in `GET /health`, and falls back to the mock detector so the dashboard remains usable.

The current v1 normalization registry is intentionally narrow. The upload review keeps produce-heavy detections such as `apple`, `banana`, `dragon fruit`, `guava`, `orange`, `oren`, `pear`, `pineapple`, and `sugar apple` visible as informational-only results, while only `cucumber`, `capsicum -> bell pepper`, and `tomato` are confirmable into inventory for the recipe demo.

4. Open the docs:

```text
http://127.0.0.1:8000/docs
```

## Implemented endpoints

- `GET /health` now returns detector diagnostics including requested mode, active mode, and any fallback warning
- `GET /profile`
- `PUT /profile`
- `GET /inventory`
- `POST /inventory`
- `PATCH /inventory/{item_id}`
- `DELETE /inventory/{item_id}`
- `GET /recipes`
- `GET /metadata`
- `GET /calories/today`
- `PUT /calories/today`
- `GET /recommendations`
- `GET /shopping-list`
- `POST /scan`
- `GET /scan/{session_id}`
- `GET /scan/{session_id}/image`
- `POST /scan/confirm?session_id=...`
- `GET /demo/scenarios`
- `POST /demo/reset`
- `POST /demo/load/{scenario_id}`

## Frontend setup

1. Install frontend dependencies:

```bash
cd frontend
npm install
```

2. Copy the frontend env file:

```bash
copy .env.example .env.local
```

The frontend now talks to the backend through the same-origin Next.js proxy at `/api/backend` by default. The proxy forwards requests to `http://127.0.0.1:8000` unless `BACKEND_INTERNAL_BASE_URL` is overridden.

3. Start the frontend:

```bash
npm run dev
```

4. Open:

```text
http://127.0.0.1:3000
```

## Easy launch

After you have installed Python packages into `.venv` and run `npm install` in [frontend](D:\Ambient Intelligence\frontend), you can start everything with either of these root files:

- [launch-smart-meal-planner.ps1](D:\Ambient Intelligence\launch-smart-meal-planner.ps1)
- [launch-smart-meal-planner.bat](D:\Ambient Intelligence\launch-smart-meal-planner.bat)

The launcher now bootstraps the project automatically:

- creates `.venv` if it does not exist
- installs backend dependencies when [backend/requirements.txt](D:\Ambient Intelligence\backend\requirements.txt) changes
- creates `backend/.env` if missing
- creates `frontend/.env.local` if missing
- runs `npm install` when [frontend/package.json](D:\Ambient Intelligence\frontend\package.json) changes
- waits for backend `/health` before launching the frontend window
- prints detector fallback warnings if YOLO is unavailable

You still need Python and Node.js installed on Windows, but you no longer need to run the setup commands manually every time.

The frontend scan panel supports two Phase 4 demo modes:

- Upload a real fridge image and let the backend persist it for YOLO-backed review
- Use the legacy sample names such as `breakfast-fridge.jpg`, `veggie-fridge.jpg`, or `protein-fridge.jpg` only when the backend is explicitly in mock mode

Sample image assets are included in [breakfast-fridge.svg](D:\Ambient Intelligence\frontend\public\demo-scans\breakfast-fridge.svg), [veggie-fridge.svg](D:\Ambient Intelligence\frontend\public\demo-scans\veggie-fridge.svg), and [protein-fridge.svg](D:\Ambient Intelligence\frontend\public\demo-scans\protein-fridge.svg).

## Demo workflow

Use the dashboard's "Scenario Loader" panel or the local scripts below to get back to a known demo state quickly:

```bash
python backend/scripts/reset_demo_state.py
python backend/scripts/load_demo_scenario.py breakfast_boost
python backend/scripts/load_demo_scenario.py veggie_reset
python backend/scripts/load_demo_scenario.py protein_recovery
```

## Tests

The current backend tests avoid external dependencies and validate the bootstrap layer, Phase 2 integration flows, Phase 4 uploaded scan handling, Phase 5 intelligence upgrades, and the Phase 6 demo/reset workflows:

```bash
python -m unittest discover backend/tests -v
```
