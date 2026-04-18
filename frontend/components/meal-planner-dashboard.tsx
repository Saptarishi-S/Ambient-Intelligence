"use client";

import { useEffect, useState } from "react";
import {
  ApiError,
  API_BASE_URL,
  confirmScan,
  createInventoryItem,
  createScan,
  deleteInventoryItem,
  fetchBackendHealth,
  fetchDemoScenarios,
  fetchCalories,
  fetchInventory,
  fetchMetadata,
  fetchRecommendations,
  fetchRecipes,
  fetchProfile,
  fetchShoppingList,
  loadDemoScenario,
  resetDemoState,
  uploadScanImage,
  updateCalories,
  updateInventoryItem,
  updateProfile
} from "@/lib/api";
import {
  buildInventoryMutationPayload,
  mergeInventoryItemsIntoSnapshot,
  normalizeInventorySnapshot,
  removeInventoryItemFromSnapshot,
  upsertInventoryItemInSnapshot
} from "@/lib/inventory";
import type {
  BackendHealth,
  DailyCalorieSummary,
  DemoScenarioSummary,
  InventoryItem,
  MetadataResponse,
  Recommendation,
  Recipe,
  ScanResult,
  ShoppingList,
  UserProfile
} from "@/lib/types";

type InventoryFormState = { name: string; quantity: string; unit: string; category: string };
type ProfileFormState = {
  name: string;
  dietary_preference: string;
  allergens: string;
  health_goal: string;
  calorie_target: string;
  preference_tags: string;
};
type CalorieFormState = { consumed: string; burned: string };

const EMPTY_INVENTORY_FORM: InventoryFormState = { name: "", quantity: "1", unit: "item", category: "pantry" };

const parseList = (value: string) => value.split(",").map((item) => item.trim()).filter(Boolean);
const percent = (value: number) => `${Math.round(value * 100)}%`;
const thresholdLabel = (value: number | null) => (value === null ? "n/a" : value.toFixed(2));

function profileToForm(profile: UserProfile): ProfileFormState {
  return {
    name: profile.name,
    dietary_preference: profile.dietary_preference,
    allergens: profile.allergens.join(", "),
    health_goal: profile.health_goal,
    calorie_target: String(profile.calorie_target),
    preference_tags: profile.preference_tags.join(", ")
  };
}

function calorieToForm(summary: DailyCalorieSummary): CalorieFormState {
  return { consumed: String(summary.consumed), burned: String(summary.burned) };
}

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError || error instanceof Error) return error.message;
  return "Unexpected error while talking to the backend.";
}

export function MealPlannerDashboard() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [metadata, setMetadata] = useState<MetadataResponse>({});
  const [calories, setCalories] = useState<DailyCalorieSummary | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [shoppingList, setShoppingList] = useState<ShoppingList>({});
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [acceptedDetections, setAcceptedDetections] = useState<string[]>([]);
  const [selectedRecipeIds, setSelectedRecipeIds] = useState<number[]>([]);
  const [demoScenarios, setDemoScenarios] = useState<DemoScenarioSummary[]>([]);
  const [activeScenarioId, setActiveScenarioId] = useState<string>("");
  const [profileForm, setProfileForm] = useState<ProfileFormState | null>(null);
  const [inventoryForm, setInventoryForm] = useState<InventoryFormState>(EMPTY_INVENTORY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [calorieForm, setCalorieForm] = useState<CalorieFormState | null>(null);
  const [scanImageName, setScanImageName] = useState("breakfast-fridge.jpg");
  const [scanFile, setScanFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("Connect the backend to start the kitchen loop.");
  const [error, setError] = useState<string | null>(null);
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);

  const recipeLookup = new Map(recipes.map((recipe) => [recipe.id, recipe]));
  const categoryOptions = (metadata.ingredient_categories?.length
    ? metadata.ingredient_categories
    : [{ value: "pantry", description: "Fallback category", sort_order: 0 }]).map((item) => item.value);

  useEffect(() => {
    void loadDashboard();
  }, []);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const healthData = await fetchBackendHealth();
      setBackendHealth(healthData);

      const [profileData, inventoryData, recipeData, metadataData, calorieData, recommendationData, shoppingData] =
        await Promise.all([
          fetchProfile(),
          fetchInventory(),
          fetchRecipes(),
          fetchMetadata(),
          fetchCalories(),
          fetchRecommendations(4),
          fetchShoppingList([], 1)
        ]);

      setProfile(profileData);
      setInventory(normalizeInventorySnapshot(inventoryData));
      setRecipes(recipeData);
      setMetadata(metadataData);
      setCalories(calorieData);
      setRecommendations(recommendationData);
      setShoppingList(shoppingData);
      setProfileForm(profileToForm(profileData));
      setCalorieForm(calorieToForm(calorieData));
      setMessage(
        healthData.detector_warning
          ? `Dashboard synced with the FastAPI backend. Detector fallback active: ${healthData.detector_warning}`
          : "Dashboard synced with the FastAPI backend."
      );
    } catch (caughtError) {
      setBackendHealth(null);
      setMessage("Waiting for the backend connection.");
      setError(`Backend unavailable or still starting. ${getErrorMessage(caughtError)}`);
    } finally {
      try {
        setDemoScenarios(await fetchDemoScenarios());
      } catch {
        setDemoScenarios([]);
      }
      setLoading(false);
    }
  }

  async function refreshRecommendations(recipeIds: number[] = selectedRecipeIds) {
    const nextRecommendations = await fetchRecommendations(4);
    const validSelection = recipeIds.filter((id) => nextRecommendations.some((item) => item.recipe_id === id));
    setRecommendations(nextRecommendations);
    setSelectedRecipeIds(validSelection);
    if (!nextRecommendations.length) {
      setShoppingList({});
      return;
    }
    await syncShoppingList(validSelection);
  }

  async function syncShoppingList(recipeIds: number[]) {
    try {
      setShoppingList(await fetchShoppingList(recipeIds, 1));
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
    }
  }

  async function revalidateInventoryAndReasoning(recipeIds: number[] = selectedRecipeIds) {
    try {
      const nextInventory = await fetchInventory();
      setInventory(normalizeInventorySnapshot(nextInventory));
    } catch (caughtError) {
      setError(`Inventory updated, but the latest inventory refresh failed. ${getErrorMessage(caughtError)}`);
      return;
    }

    try {
      await refreshRecommendations(recipeIds);
    } catch (caughtError) {
      setError(`Inventory updated, but recommendations could not be refreshed. ${getErrorMessage(caughtError)}`);
    }
  }

  function applySavedInventoryItem(item: InventoryItem) {
    setInventory((current) => upsertInventoryItemInSnapshot(current, item));
  }

  function applyInventoryUpdates(items: InventoryItem[]) {
    setInventory((current) => mergeInventoryItemsIntoSnapshot(current, items));
  }

  function applyRemovedInventoryItem(itemId: number) {
    setInventory((current) => removeInventoryItemFromSnapshot(current, itemId));
  }

  async function runAction(key: string, successMessage: string, action: () => Promise<void>) {
    setBusy(key);
    setError(null);
    try {
      await action();
      setMessage(successMessage);
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
    } finally {
      setBusy(null);
    }
  }

  function resetInventoryForm() {
    setEditingId(null);
    setInventoryForm(EMPTY_INVENTORY_FORM);
  }

  async function saveInventoryItem() {
    let payload: ReturnType<typeof buildInventoryMutationPayload>;
    try {
      payload = buildInventoryMutationPayload(inventoryForm);
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
      return;
    }

    const currentEditingId = editingId;
    await runAction("inventory", currentEditingId ? "Inventory item updated." : "Inventory item added.", async () => {
      const savedItem = currentEditingId
        ? await updateInventoryItem(currentEditingId, payload)
        : await createInventoryItem(payload);
      applySavedInventoryItem(savedItem);
      resetInventoryForm();
      await revalidateInventoryAndReasoning();
    });
  }

  const scanPreviewUrl = scan?.image_url ? `${API_BASE_URL}${scan.image_url}` : null;

  async function toggleRecipeSelection(recipeId: number) {
    const nextSelection = selectedRecipeIds.includes(recipeId)
      ? selectedRecipeIds.filter((id) => id !== recipeId)
      : [...selectedRecipeIds, recipeId];

    setSelectedRecipeIds(nextSelection);

    if (!recommendations.length) {
      setShoppingList({});
      return;
    }

    await syncShoppingList(nextSelection);
  }

  function applyDemoSnapshot(snapshot: {
    profile: UserProfile;
    inventory: InventoryItem[];
    calories: DailyCalorieSummary;
    recommendations: Recommendation[];
    active_scenario?: DemoScenarioSummary;
  }) {
    setProfile(snapshot.profile);
    setProfileForm(profileToForm(snapshot.profile));
    setInventory(normalizeInventorySnapshot(snapshot.inventory));
    setCalories(snapshot.calories);
    setCalorieForm(calorieToForm(snapshot.calories));
    setRecommendations(snapshot.recommendations);
    setSelectedRecipeIds([]);
    setShoppingList({});
    setActiveScenarioId(snapshot.active_scenario?.id ?? "");
  }

  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Ambient Intelligence Kitchen Assistant</p>
          <h1>Smart Meal Planner</h1>
          <p className="hero-copy">
            Review the user profile, maintain fridge inventory, simulate scans, and watch the recommendation engine
            rank recipes around what is already available.
          </p>
        </div>
        <div className="hero-stats">
          <div className="stat-chip"><span>Backend</span><strong>{API_BASE_URL}</strong></div>
          <div className="stat-chip"><span>User</span><strong>{profile?.name ?? "Demo User"}</strong></div>
          <div className="stat-chip"><span>Inventory</span><strong>{inventory.length} tracked items</strong></div>
          <div className="stat-chip"><span>Detector</span><strong>{backendHealth?.detector_active ?? "offline"}</strong></div>
        </div>
      </section>

      <section className="status-row">
        <div className="status-card"><span className="status-label">Status</span><p>{loading ? "Loading..." : message}</p></div>
        {backendHealth ? (
          <div className="status-card">
            <span className="status-label">Backend Health</span>
            <p>
              Requested {backendHealth.detector_requested}, active {backendHealth.detector_active}.
              {backendHealth.detector_warning ? ` ${backendHealth.detector_warning}` : " Detector ready."}
            </p>
          </div>
        ) : null}
        {error ? <div className="status-card status-card-error"><span className="status-label">Issue</span><p>{error}</p></div> : null}
      </section>

      <section className="dashboard-grid">
        <article className="panel">
          <div className="panel-header"><div><p className="panel-kicker">Demo Controls</p><h2>Scenario Loader</h2></div></div>
          <div className="stack-form">
            <label>
              <span>Scripted scenario</span>
              <select value={activeScenarioId} onChange={(event) => setActiveScenarioId(event.target.value)}>
                <option value="">Select a scenario</option>
                {demoScenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.name}</option>)}
              </select>
            </label>
            <p className="helper-text">
              {activeScenarioId
                ? demoScenarios.find((scenario) => scenario.id === activeScenarioId)?.description
                : "Load a preset profile, calorie summary, and inventory snapshot for a clean demo run."}
            </p>
            <button className="secondary-button" disabled={!activeScenarioId || busy === "load-demo" || !demoScenarios.length} onClick={() => void runAction("load-demo", "Demo scenario loaded.", async () => {
              const snapshot = await loadDemoScenario(activeScenarioId);
              applyDemoSnapshot(snapshot);
              await revalidateInventoryAndReasoning([]);
            })} type="button">
              {busy === "load-demo" ? "Loading..." : "Load scenario"}
            </button>
            <button className="text-button" disabled={busy === "reset-demo"} onClick={() => void runAction("reset-demo", "Demo state reset to defaults.", async () => {
              const snapshot = await resetDemoState();
              applyDemoSnapshot(snapshot);
              setScan(null);
              setAcceptedDetections([]);
              await revalidateInventoryAndReasoning([]);
            })} type="button">
              {busy === "reset-demo" ? "Resetting..." : "Reset demo state"}
            </button>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header"><div><p className="panel-kicker">Context Layer</p><h2>Profile and Goals</h2></div></div>
          {profileForm ? (
            <form className="stack-form" onSubmit={(event) => {
              event.preventDefault();
              void runAction("profile", "Profile updated and recommendations refreshed.", async () => {
                const nextProfile = await updateProfile({
                  name: profileForm.name,
                  dietary_preference: profileForm.dietary_preference as UserProfile["dietary_preference"],
                  allergens: parseList(profileForm.allergens),
                  health_goal: profileForm.health_goal as UserProfile["health_goal"],
                  calorie_target: Number(profileForm.calorie_target),
                  preference_tags: parseList(profileForm.preference_tags)
                });
                setProfile(nextProfile);
                setProfileForm(profileToForm(nextProfile));
                await refreshRecommendations();
              });
            }}>
              <label><span>Name</span><input value={profileForm.name} onChange={(event) => setProfileForm({ ...profileForm, name: event.target.value })} /></label>
              <label><span>Dietary preference</span><select value={profileForm.dietary_preference} onChange={(event) => setProfileForm({ ...profileForm, dietary_preference: event.target.value })}>{(metadata.dietary_tags ?? []).map((item) => <option key={item.value} value={item.value}>{item.value}</option>)}</select></label>
              <label><span>Health goal</span><select value={profileForm.health_goal} onChange={(event) => setProfileForm({ ...profileForm, health_goal: event.target.value })}>{(metadata.health_goals ?? []).map((item) => <option key={item.value} value={item.value}>{item.value}</option>)}</select></label>
              <label><span>Allergens</span><input placeholder="dairy, soy" value={profileForm.allergens} onChange={(event) => setProfileForm({ ...profileForm, allergens: event.target.value })} /></label>
              <label><span>Preference tags</span><input placeholder="quick, balanced" value={profileForm.preference_tags} onChange={(event) => setProfileForm({ ...profileForm, preference_tags: event.target.value })} /></label>
              <label><span>Daily calorie target</span><input type="number" min="0" value={profileForm.calorie_target} onChange={(event) => setProfileForm({ ...profileForm, calorie_target: event.target.value })} /></label>
              <button className="primary-button" disabled={busy === "profile"} type="submit">{busy === "profile" ? "Saving..." : "Save profile"}</button>
            </form>
          ) : null}
        </article>

        <article className="panel">
          <div className="panel-header"><div><p className="panel-kicker">Health Snapshot</p><h2>Calories</h2></div></div>
          {calories && calorieForm ? (
            <>
              <div className="metric-band">
                <div><span>Consumed</span><strong>{calories.consumed}</strong></div>
                <div><span>Burned</span><strong>{calories.burned}</strong></div>
                <div><span>Net</span><strong>{calories.consumed - calories.burned}</strong></div>
              </div>
              <form className="stack-form" onSubmit={(event) => {
                event.preventDefault();
                void runAction("calories", "Daily calorie summary updated.", async () => {
                  const summary = await updateCalories({ consumed: Number(calorieForm.consumed), burned: Number(calorieForm.burned) });
                  setCalories(summary);
                  setCalorieForm(calorieToForm(summary));
                });
              }}>
                <label><span>Consumed today</span><input type="number" min="0" value={calorieForm.consumed} onChange={(event) => setCalorieForm({ ...calorieForm, consumed: event.target.value })} /></label>
                <label><span>Burned today</span><input type="number" min="0" value={calorieForm.burned} onChange={(event) => setCalorieForm({ ...calorieForm, burned: event.target.value })} /></label>
                <button className="secondary-button" disabled={busy === "calories"} type="submit">{busy === "calories" ? "Updating..." : "Update calories"}</button>
              </form>
            </>
          ) : null}
        </article>

        <article className="panel panel-wide">
          <div className="panel-header">
            <div><p className="panel-kicker">Inventory Layer</p><h2>Inventory Editor</h2></div>
            {editingId ? <button className="text-button" onClick={resetInventoryForm} type="button">Cancel edit</button> : null}
          </div>
          <form className="inventory-form" onSubmit={(event) => {
            event.preventDefault();
            void saveInventoryItem();
          }}>
            <input placeholder="ingredient" value={inventoryForm.name} onChange={(event) => setInventoryForm({ ...inventoryForm, name: event.target.value })} />
            <input type="number" min="0.1" step="0.1" value={inventoryForm.quantity} onChange={(event) => setInventoryForm({ ...inventoryForm, quantity: event.target.value })} />
            <input value={inventoryForm.unit} onChange={(event) => setInventoryForm({ ...inventoryForm, unit: event.target.value })} />
            <select value={inventoryForm.category} onChange={(event) => setInventoryForm({ ...inventoryForm, category: event.target.value })}>
              {categoryOptions.map((category) => <option key={category} value={category}>{category}</option>)}
            </select>
            <button className="primary-button" disabled={busy === "inventory"} type="submit">{busy === "inventory" ? "Saving..." : editingId ? "Update item" : "Add item"}</button>
          </form>
          <div className="inventory-list">
            {inventory.length ? inventory.map((item) => (
              <div className="inventory-row" key={item.id}>
                <div><strong>{item.name}</strong><p>{item.quantity} {item.unit} - {item.category} - {item.source}</p></div>
                <div className="row-actions">
                  <button className="text-button" onClick={() => { setEditingId(item.id); setInventoryForm({ name: item.name, quantity: String(item.quantity), unit: item.unit, category: item.category }); }} type="button">Edit</button>
                  <button className="text-button text-button-danger" disabled={busy === `delete-${item.id}`} onClick={() => void runAction(`delete-${item.id}`, "Inventory item removed.", async () => { await deleteInventoryItem(item.id); if (editingId === item.id) resetInventoryForm(); applyRemovedInventoryItem(item.id); await revalidateInventoryAndReasoning(); })} type="button">Delete</button>
                </div>
              </div>
            )) : <p className="empty-state">No ingredients tracked yet.</p>}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header"><div><p className="panel-kicker">Perception Layer</p><h2>Fridge Scan Review</h2></div></div>
          <form className="stack-form" onSubmit={(event) => {
            event.preventDefault();
            void runAction("scan", "Scan completed. Review detections before confirming.", async () => {
              const nextScan = scanFile ? await uploadScanImage(scanFile, scanImageName || scanFile.name) : await createScan(scanImageName);
              setScan(nextScan);
              setAcceptedDetections(nextScan.detections.filter((item) => item.supported).map((item) => item.ingredient_name));
            });
          }}>
            <label>
              <span>Upload a fridge image</span>
              <input
                accept="image/*"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setScanFile(file);
                  if (file) {
                    setScanImageName(file.name);
                  }
                }}
                type="file"
              />
            </label>
            <label><span>Image name</span><input value={scanImageName} onChange={(event) => setScanImageName(event.target.value)} /></label>
            <p className="helper-text">Upload a real fridge image for YOLO mode. The sample names `breakfast-fridge.jpg`, `veggie-fridge.jpg`, and `protein-fridge.jpg` are reserved for explicit mock mode.</p>
            <button className="secondary-button" disabled={busy === "scan"} type="submit">{busy === "scan" ? "Scanning..." : scanFile ? "Upload and scan" : "Run sample scan"}</button>
          </form>
          {scan ? (
            <div className="scan-review">
              <div className="scan-heading"><strong>{scan.image_name}</strong><span>{scan.created_at}</span></div>
              {scanPreviewUrl ? <img alt={scan.image_name} className="scan-preview" src={scanPreviewUrl} /> : null}
              <p className="helper-text">
                Detector: {scan.detector}
                {scan.model_name ? ` - Model: ${scan.model_name}` : ""}
                {` - Threshold: ${thresholdLabel(scan.confidence_threshold)}`}
                {scan.image_size_bytes ? ` - ${scan.image_size_bytes} bytes` : ""}
              </p>
              {scan.detections.length ? scan.detections.map((item, index) => (
                <label className="detection-row" key={`${scan.session_id}-${item.model_label}-${index}`}>
                  <input checked={item.supported && acceptedDetections.includes(item.ingredient_name)} disabled={!item.supported} onChange={(event) => setAcceptedDetections((current) => event.target.checked ? [...new Set([...current, item.ingredient_name])] : current.filter((name) => name !== item.ingredient_name))} type="checkbox" />
                  <span>
                    {item.ingredient_name}
                    {item.model_label !== item.ingredient_name ? ` (model: ${item.model_label})` : ""}
                    {` - ${item.quantity} ${item.unit} - ${percent(item.confidence)} - ${item.supported ? "supported" : "informational only"}`}
                  </span>
                </label>
              )) : <p className="empty-state">No supported or informational detections cleared the configured threshold.</p>}
              <p className="helper-text">Only supported detections are confirmable in v1 so fruit-only labels stay visible in review without reshaping the recipe demo.</p>
              <button className="primary-button" disabled={busy === "confirm-scan" || !acceptedDetections.length} onClick={() => void runAction("confirm-scan", "Selected detections added to inventory.", async () => { if (!scan) return; const result = await confirmScan(scan.session_id, acceptedDetections); applyInventoryUpdates(result.inventory_updates); await revalidateInventoryAndReasoning(); })} type="button">{busy === "confirm-scan" ? "Confirming..." : "Add selected to inventory"}</button>
            </div>
          ) : null}
        </article>

        <article className="panel panel-wide">
          <div className="panel-header"><div><p className="panel-kicker">Reasoning Engine</p><h2>Recipe Recommendations</h2></div></div>
          <div className="recommendation-grid">
            {recommendations.length ? recommendations.map((item) => {
              const recipe = recipeLookup.get(item.recipe_id);
              const selected = selectedRecipeIds.includes(item.recipe_id);
              return (
                <article className={`recipe-card ${selected ? "recipe-card-selected" : ""}`} key={item.recipe_id}>
                  <div className="recipe-card-top">
                    <div><h3>{item.recipe_title}</h3><p>{recipe?.description ?? item.explanation}</p></div>
                    <button className="text-button" onClick={() => void toggleRecipeSelection(item.recipe_id)} type="button">{selected ? "Included in list" : "Use for shopping list"}</button>
                  </div>
                  <div className="score-strip"><span>Score {item.score.toFixed(2)}</span><span>Ingredient match {percent(item.ingredient_match_ratio)}</span><span>Health fit {percent(item.health_goal_alignment)}</span></div>
                  <div className="score-strip"><span>Calorie fit {percent(item.calorie_fit_score)}</span><span>Protein fit {percent(item.protein_fit_score)}</span><span>Macro balance {percent(item.macro_balance_score)}</span></div>
                  <div className="recipe-meta"><span>{recipe?.prep_minutes ?? "--"} min</span><span>{recipe?.calories ?? "--"} kcal</span><span>{recipe?.protein ?? "--"}g protein</span></div>
                  <p className="explanation">{item.explanation}</p>
                  <div className="tag-row">
                    {item.matched_ingredients.map((match) => <span className="tag tag-good" key={`match-${item.recipe_id}-${match}`}>{match}</span>)}
                    {item.missing_ingredients.map((missing) => <span className="tag tag-missing" key={`missing-${item.recipe_id}-${missing}`}>{missing}</span>)}
                  </div>
                </article>
              );
            }) : <p className="empty-state">No compatible recipes yet.</p>}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header"><div><p className="panel-kicker">Action Layer</p><h2>Shopping List</h2></div></div>
          <p className="helper-text">{selectedRecipeIds.length ? "Built from the cards you selected." : "Using the top recommendation by default."}</p>
          {Object.keys(shoppingList).length ? (
            <div className="shopping-groups">
              {Object.entries(shoppingList).map(([category, items]) => (
                <div className="shopping-group" key={category}>
                  <h3>{category}</h3>
                  {items.map((item) => <div className="shopping-item" key={`${category}-${item.name}`}><span>{item.name}</span><strong>{item.quantity} {item.unit}</strong></div>)}
                </div>
              ))}
            </div>
          ) : <p className="empty-state">No missing ingredients for the selected recipe set.</p>}
        </article>
      </section>
    </main>
  );
}
