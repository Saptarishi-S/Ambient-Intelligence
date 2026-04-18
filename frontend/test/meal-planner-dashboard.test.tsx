import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { MealPlannerDashboard } from "@/components/meal-planner-dashboard";
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

import { server } from "./server";

const TIMESTAMP = "2026-04-10T10:00:00Z";

function apiUrl(path: string) {
  return new URL(`/api/backend${path}`, window.location.origin).toString();
}

type DemoScenario = {
  id: string;
  name: string;
  description: string;
  inventory: InventoryItem[];
  profile: UserProfile;
  calories: DailyCalorieSummary;
};

type MockApiState = {
  calories: DailyCalorieSummary;
  inventory: InventoryItem[];
  nextInventoryId: number;
  profile: UserProfile;
  recipes: Recipe[];
  metadata: MetadataResponse;
  scanResult: ScanResult;
  scenarios: DemoScenario[];
  defaultInventory: InventoryItem[];
};

function buildInventoryItem(
  id: number,
  name: string,
  quantity: number,
  unit: string,
  category: string,
  source = "manual"
): InventoryItem {
  return {
    id,
    name,
    quantity,
    unit,
    category,
    source,
    confidence: null,
    last_updated: TIMESTAMP
  };
}

function sortInventory(items: InventoryItem[]) {
  return [...items].sort((left, right) => left.name.localeCompare(right.name));
}

function buildRecipes(): Recipe[] {
  return [
    {
      id: 1,
      title: "Spinach Omelette",
      description: "Eggs, spinach, and cheese.",
      dietary_tags: ["vegetarian"],
      allergens: ["dairy"],
      preference_tags: ["quick"],
      calories: 390,
      protein: 25,
      carbs: 8,
      fat: 28,
      prep_minutes: 12,
      instructions: ["Cook and serve."],
      ingredients: [
        { name: "egg", quantity: 2, unit: "item", category: "protein", optional: false },
        { name: "spinach", quantity: 1, unit: "cup", category: "produce", optional: false },
        { name: "cheese", quantity: 0.25, unit: "cup", category: "dairy", optional: false }
      ]
    },
    {
      id: 2,
      title: "Rice Power Bowl",
      description: "Rice and broccoli with olive oil.",
      dietary_tags: ["vegan", "vegetarian"],
      allergens: [],
      preference_tags: ["balanced"],
      calories: 510,
      protein: 19,
      carbs: 68,
      fat: 17,
      prep_minutes: 20,
      instructions: ["Assemble the bowl."],
      ingredients: [
        { name: "rice", quantity: 1, unit: "cup", category: "grains", optional: false },
        { name: "broccoli", quantity: 1, unit: "cup", category: "produce", optional: false },
        { name: "olive oil", quantity: 1, unit: "tbsp", category: "condiments", optional: true }
      ]
    }
  ];
}

function buildMetadata(): MetadataResponse {
  return {
    ingredient_categories: [
      { value: "protein", description: "Protein", sort_order: 1 },
      { value: "produce", description: "Produce", sort_order: 2 },
      { value: "grains", description: "Grains", sort_order: 3 },
      { value: "dairy", description: "Dairy", sort_order: 4 },
      { value: "pantry", description: "Pantry", sort_order: 5 },
      { value: "condiments", description: "Condiments", sort_order: 6 }
    ],
    dietary_tags: [
      { value: "omnivore", description: "Omnivore", sort_order: 1 },
      { value: "vegetarian", description: "Vegetarian", sort_order: 2 },
      { value: "vegan", description: "Vegan", sort_order: 3 }
    ],
    health_goals: [
      { value: "maintenance", description: "Maintenance", sort_order: 1 },
      { value: "weight_loss", description: "Weight loss", sort_order: 2 },
      { value: "muscle_gain", description: "Muscle gain", sort_order: 3 }
    ]
  };
}

function buildProfile(): UserProfile {
  return {
    id: 1,
    name: "Demo User",
    dietary_preference: "omnivore",
    allergens: [],
    health_goal: "maintenance",
    calorie_target: 2200,
    preference_tags: ["quick", "balanced"]
  };
}

function buildCalories(): DailyCalorieSummary {
  return {
    date: "2026-04-10",
    consumed: 1450,
    burned: 520
  };
}

function buildHealth(overrides: Partial<BackendHealth> = {}): BackendHealth {
  return {
    status: "ok",
    version: "0.6.0",
    detector_requested: "mock",
    detector_active: "mock",
    detector_warning: null,
    max_upload_size_bytes: 5242880,
    ...overrides
  };
}

function buildRecommendations(recipes: Recipe[], inventory: InventoryItem[]): Recommendation[] {
  const inventoryNames = new Set(inventory.map((item) => item.name));
  return [...recipes]
    .map((recipe) => {
      const requiredIngredients = recipe.ingredients.filter((ingredient) => !ingredient.optional);
      const matched = requiredIngredients
        .filter((ingredient) => inventoryNames.has(ingredient.name))
        .map((ingredient) => ingredient.name);
      const missing = requiredIngredients
        .filter((ingredient) => !inventoryNames.has(ingredient.name))
        .map((ingredient) => ingredient.name);
      const score = matched.length / Math.max(requiredIngredients.length, 1);
      return {
        recipe_id: recipe.id,
        recipe_title: recipe.title,
        score,
        explanation: missing.length ? `Needs ${missing.join(", ")}.` : "Ready to cook.",
        ingredient_match_ratio: score,
        missing_items_ratio: missing.length / Math.max(requiredIngredients.length, 1),
        health_goal_alignment: 0.8,
        user_preference_match: 0.7,
        calorie_fit_score: 0.75,
        protein_fit_score: 0.7,
        macro_balance_score: 0.8,
        narrative_style: "test-double",
        matched_ingredients: matched,
        missing_ingredients: missing
      };
    })
    .sort((left, right) => right.score - left.score);
}

function buildShoppingList(recipes: Recipe[], recommendations: Recommendation[], recipeIds: number[]): ShoppingList {
  const effectiveRecipeIds = recipeIds.length ? recipeIds : recommendations.slice(0, 1).map((item) => item.recipe_id);
  const grouped = new Map<string, Map<string, { name: string; quantity: number; unit: string; category: string }>>();

  for (const recipeId of effectiveRecipeIds) {
    const recipe = recipes.find((candidate) => candidate.id === recipeId);
    const recommendation = recommendations.find((candidate) => candidate.recipe_id === recipeId);
    if (!recipe || !recommendation) {
      continue;
    }

    const missingNames = new Set(recommendation.missing_ingredients);
    for (const ingredient of recipe.ingredients) {
      if (!missingNames.has(ingredient.name)) {
        continue;
      }
      const categoryBucket = grouped.get(ingredient.category) ?? new Map();
      const existing = categoryBucket.get(ingredient.name);
      if (existing) {
        existing.quantity += ingredient.quantity;
      } else {
        categoryBucket.set(ingredient.name, {
          name: ingredient.name,
          quantity: ingredient.quantity,
          unit: ingredient.unit,
          category: ingredient.category
        });
      }
      grouped.set(ingredient.category, categoryBucket);
    }
  }

  return Object.fromEntries(
    [...grouped.entries()].map(([category, items]) => [
      category,
      [...items.values()].sort((left, right) => left.name.localeCompare(right.name))
    ])
  );
}

function createMockApiState(initialInventory: InventoryItem[]): MockApiState {
  const recipes = buildRecipes();
  const profile = buildProfile();
  const calories = buildCalories();
  const inventory = sortInventory(initialInventory);
  const scenarios: DemoScenario[] = [
    {
      id: "veggie_reset",
      name: "Veggie Reset",
      description: "A produce-heavy scenario for demos.",
      inventory: sortInventory([
        buildInventoryItem(11, "broccoli", 1, "cup", "produce"),
        buildInventoryItem(12, "rice", 1, "cup", "grains")
      ]),
      profile,
      calories
    }
  ];

  return {
    calories,
    defaultInventory: sortInventory(initialInventory),
    inventory,
    metadata: buildMetadata(),
    nextInventoryId: 100,
    profile,
    recipes,
    scanResult: {
      session_id: "scan-session-1",
      image_name: "breakfast-fridge.jpg",
      detections: [
        {
          ingredient_name: "spinach",
          model_label: "spinach",
          confidence: 0.92,
          category: "produce",
          quantity: 1,
          unit: "cup",
          supported: true
        }
      ],
      created_at: TIMESTAMP,
      image_mime_type: null,
      image_size_bytes: null,
      image_url: null,
      detector: "mock-upload-v1",
      model_name: null,
      confidence_threshold: null
    },
    scenarios
  };
}

function createScenarioSnapshot(state: MockApiState, scenario: DemoScenario) {
  return {
    profile: scenario.profile,
    inventory: scenario.inventory,
    calories: scenario.calories,
    recommendations: buildRecommendations(state.recipes, scenario.inventory),
    active_scenario: {
      id: scenario.id,
      name: scenario.name,
      description: scenario.description
    }
  };
}

function installApiHandlers(state: MockApiState) {
  server.use(
    http.get(apiUrl("/health"), () => HttpResponse.json(buildHealth())),
    http.get(apiUrl("/profile"), () => HttpResponse.json(state.profile)),
    http.get(apiUrl("/inventory"), () => HttpResponse.json(state.inventory)),
    http.get(apiUrl("/recipes"), () => HttpResponse.json(state.recipes)),
    http.get(apiUrl("/metadata"), () => HttpResponse.json(state.metadata)),
    http.get(apiUrl("/calories/today"), () => HttpResponse.json(state.calories)),
    http.get(apiUrl("/recommendations"), ({ request }) => {
      const url = new URL(request.url);
      const limit = Number(url.searchParams.get("limit") ?? "4");
      return HttpResponse.json(buildRecommendations(state.recipes, state.inventory).slice(0, limit));
    }),
    http.get(apiUrl("/shopping-list"), ({ request }) => {
      const url = new URL(request.url);
      const recipeIds = (url.searchParams.get("recipe_ids") ?? "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean)
        .map((value) => Number(value));
      return HttpResponse.json(buildShoppingList(state.recipes, buildRecommendations(state.recipes, state.inventory), recipeIds));
    }),
    http.get(apiUrl("/demo/scenarios"), () => {
      const summaries: DemoScenarioSummary[] = state.scenarios.map((scenario) => ({
        id: scenario.id,
        name: scenario.name,
        description: scenario.description
      }));
      return HttpResponse.json(summaries);
    }),
    http.post(apiUrl("/inventory"), async ({ request }) => {
      const payload = (await request.json()) as Partial<InventoryItem>;
      const nextItem = buildInventoryItem(
        state.nextInventoryId++,
        String(payload.name ?? "").trim().toLowerCase(),
        Number(payload.quantity ?? 1),
        String(payload.unit ?? "item").trim().toLowerCase(),
        String(payload.category ?? "pantry").trim().toLowerCase()
      );
      state.inventory = sortInventory([...state.inventory, nextItem]);
      return HttpResponse.json(nextItem, { status: 201 });
    }),
    http.patch(apiUrl("/inventory/:itemId"), async ({ params, request }) => {
      const itemId = Number(params.itemId);
      const payload = (await request.json()) as Partial<InventoryItem>;
      const current = state.inventory.find((item) => item.id === itemId);
      if (!current) {
        return HttpResponse.json({ detail: `Inventory item ${itemId} not found.` }, { status: 404 });
      }

      const updated = {
        ...current,
        name: payload.name ? String(payload.name).trim().toLowerCase() : current.name,
        quantity: payload.quantity !== undefined ? Number(payload.quantity) : current.quantity,
        unit: payload.unit ? String(payload.unit).trim().toLowerCase() : current.unit,
        category: payload.category ? String(payload.category).trim().toLowerCase() : current.category,
        last_updated: TIMESTAMP
      };
      state.inventory = sortInventory(
        state.inventory.map((item) => (item.id === itemId ? updated : item))
      );
      return HttpResponse.json(updated);
    }),
    http.delete(apiUrl("/inventory/:itemId"), ({ params }) => {
      const itemId = Number(params.itemId);
      state.inventory = state.inventory.filter((item) => item.id !== itemId);
      return new HttpResponse(null, { status: 204 });
    }),
    http.post(apiUrl("/scan"), () => HttpResponse.json(state.scanResult, { status: 201 })),
    http.post(apiUrl("/scan/confirm"), async ({ request }) => {
      const payload = (await request.json()) as { accepted_ingredients?: string[] };
      const acceptedNames = new Set(payload.accepted_ingredients ?? []);
      const accepted = state.scanResult.detections.filter((item) => item.supported && acceptedNames.has(item.ingredient_name));
      const updates: InventoryItem[] = [];

      for (const detection of accepted) {
        const existing = state.inventory.find((item) => item.name === detection.ingredient_name);
        if (existing) {
          const updated = {
            ...existing,
            quantity: existing.quantity + detection.quantity,
            source: "scan",
            last_updated: TIMESTAMP
          };
          state.inventory = state.inventory.map((item) => (item.id === updated.id ? updated : item));
          updates.push(updated);
        } else {
          const created = buildInventoryItem(
            state.nextInventoryId++,
            detection.ingredient_name,
            detection.quantity,
            detection.unit,
            detection.category,
            "scan"
          );
          state.inventory = [...state.inventory, created];
          updates.push(created);
        }
      }

      state.inventory = sortInventory(state.inventory);
      return HttpResponse.json({
        scan_result: state.scanResult,
        accepted,
        inventory_updates: sortInventory(updates)
      });
    }),
    http.post(apiUrl("/demo/load/:scenarioId"), ({ params }) => {
      const scenarioId = String(params.scenarioId);
      const scenario = state.scenarios.find((item) => item.id === scenarioId);
      if (!scenario) {
        return HttpResponse.json({ detail: `Demo scenario '${scenarioId}' not found.` }, { status: 404 });
      }

      state.profile = scenario.profile;
      state.calories = scenario.calories;
      state.inventory = sortInventory(scenario.inventory);
      return HttpResponse.json(createScenarioSnapshot(state, scenario));
    }),
    http.post(apiUrl("/demo/reset"), () => {
      state.profile = buildProfile();
      state.calories = buildCalories();
      state.inventory = sortInventory(state.defaultInventory);
      return HttpResponse.json({
        profile: state.profile,
        inventory: state.inventory,
        calories: state.calories,
        recommendations: buildRecommendations(state.recipes, state.inventory)
      });
    })
  );
}

function getPanel(title: string) {
  const heading = screen.getByRole("heading", { name: title });
  const panel = heading.closest("article");
  if (!panel) {
    throw new Error(`Panel '${title}' not found.`);
  }
  return within(panel);
}

function getInventoryRow(name: string) {
  const inventoryPanel = getPanel("Inventory Editor");
  const row = inventoryPanel.getByText(name).closest(".inventory-row");
  if (!row) {
    throw new Error(`Inventory row '${name}' not found.`);
  }
  return within(row as HTMLElement);
}

async function renderDashboard(initialInventory: InventoryItem[]) {
  const state = createMockApiState(initialInventory);
  installApiHandlers(state);
  render(<MealPlannerDashboard />);
  await screen.findByText("Dashboard synced with the FastAPI backend.");
  return { state, user: userEvent.setup() };
}

describe("MealPlannerDashboard inventory synchronization", () => {
  it("shows a backend unavailable message before the dashboard data can load", async () => {
    server.use(
      http.get(apiUrl("/demo/scenarios"), () => HttpResponse.json([])),
      http.get(apiUrl("/health"), () =>
        HttpResponse.json({ detail: "Backend unavailable. Start the FastAPI server." }, { status: 503 })
      )
    );

    render(<MealPlannerDashboard />);

    await screen.findByText(/Backend unavailable or still starting/i);
    expect(screen.getByText("Waiting for the backend connection.")).toBeInTheDocument();
  });

  it("adds an inventory item and refreshes the shopping list", async () => {
    const { user } = await renderDashboard([
      buildInventoryItem(1, "egg", 2, "item", "protein")
    ]);

    const inventoryPanel = getPanel("Inventory Editor");
    await user.type(inventoryPanel.getByPlaceholderText("ingredient"), "Spinach");
    await user.clear(inventoryPanel.getByRole("spinbutton"));
    await user.type(inventoryPanel.getByRole("spinbutton"), "1");
    const textboxes = inventoryPanel.getAllByRole("textbox");
    await user.clear(textboxes[1]);
    await user.type(textboxes[1], "cup");
    await user.selectOptions(inventoryPanel.getByRole("combobox"), "produce");
    await user.click(inventoryPanel.getByRole("button", { name: "Add item" }));

    await inventoryPanel.findByText("spinach");
    const shoppingPanel = getPanel("Shopping List");
    await waitFor(() => {
      expect(shoppingPanel.queryByText("spinach")).not.toBeInTheDocument();
      expect(shoppingPanel.getByText("cheese")).toBeInTheDocument();
    });
  });

  it("edits an existing inventory row without needing a reload", async () => {
    const { user } = await renderDashboard([
      buildInventoryItem(1, "rice", 1, "cup", "grains")
    ]);

    await user.click(getInventoryRow("rice").getByRole("button", { name: "Edit" }));

    const inventoryPanel = getPanel("Inventory Editor");
    const ingredientInput = inventoryPanel.getByPlaceholderText("ingredient");
    await user.clear(ingredientInput);
    await user.type(ingredientInput, "Brown Rice");
    await user.click(inventoryPanel.getByRole("button", { name: "Update item" }));

    await inventoryPanel.findByText("brown rice");
    expect(inventoryPanel.queryByText("rice")).not.toBeInTheDocument();
  });

  it("deletes the item being edited and resets the editor form", async () => {
    const { user } = await renderDashboard([
      buildInventoryItem(1, "egg", 2, "item", "protein"),
      buildInventoryItem(2, "spinach", 1, "cup", "produce")
    ]);

    const spinachRow = getInventoryRow("spinach");
    await user.click(spinachRow.getByRole("button", { name: "Edit" }));
    expect(getPanel("Inventory Editor").getByRole("button", { name: "Update item" })).toBeInTheDocument();

    await user.click(spinachRow.getByRole("button", { name: "Delete" }));

    const inventoryPanel = getPanel("Inventory Editor");
    await waitFor(() => {
      expect(inventoryPanel.queryByText("spinach")).not.toBeInTheDocument();
      expect(inventoryPanel.getByRole("button", { name: "Add item" })).toBeInTheDocument();
    });
  });

  it("keeps the saved row visible when recommendation refresh fails", async () => {
    const { user } = await renderDashboard([
      buildInventoryItem(1, "rice", 1, "cup", "grains")
    ]);

    server.use(
      http.get(apiUrl("/recommendations"), () =>
        HttpResponse.json({ detail: "Recommendation refresh failed." }, { status: 500 })
      )
    );

    await user.click(getInventoryRow("rice").getByRole("button", { name: "Edit" }));

    const inventoryPanel = getPanel("Inventory Editor");
    const ingredientInput = inventoryPanel.getByPlaceholderText("ingredient");
    await user.clear(ingredientInput);
    await user.type(ingredientInput, "Brown Rice");
    await user.click(inventoryPanel.getByRole("button", { name: "Update item" }));

    await inventoryPanel.findByText("brown rice");
    expect(screen.getByText(/recommendations could not be refreshed/i)).toBeInTheDocument();
  });

  it("adds confirmed scan detections into inventory and refreshes derived data", async () => {
    const { user } = await renderDashboard([
      buildInventoryItem(1, "egg", 2, "item", "protein")
    ]);

    const scanPanel = getPanel("Fridge Scan Review");
    await user.click(scanPanel.getByRole("button", { name: "Run sample scan" }));
    await screen.findByText(/spinach - 1 cup/i);

    await user.click(scanPanel.getByRole("button", { name: "Add selected to inventory" }));

    await getPanel("Inventory Editor").findByText("spinach");
    const shoppingPanel = getPanel("Shopping List");
    await waitFor(() => {
      expect(shoppingPanel.queryByText("spinach")).not.toBeInTheDocument();
      expect(shoppingPanel.getByText("cheese")).toBeInTheDocument();
    });
  });

  it("shows informational detections without preselecting them for confirmation", async () => {
    const { state, user } = await renderDashboard([
      buildInventoryItem(1, "tofu", 1, "pack", "protein"),
      buildInventoryItem(2, "broccoli", 1, "cup", "produce")
    ]);

    state.scanResult = {
      ...state.scanResult,
      image_name: "real-fridge.jpg",
      detections: [
        {
          ingredient_name: "bell pepper",
          model_label: "capsicum",
          confidence: 0.93,
          category: "produce",
          quantity: 1,
          unit: "item",
          supported: true
        },
        {
          ingredient_name: "orange",
          model_label: "oren",
          confidence: 0.88,
          category: "produce",
          quantity: 1,
          unit: "item",
          supported: false
        }
      ],
      detector: "yolo-ultralytics-v1",
      model_name: "YOLO_Model.pt",
      confidence_threshold: 0.35
    };

    const scanPanel = getPanel("Fridge Scan Review");
    await user.click(scanPanel.getByRole("button", { name: "Run sample scan" }));
    await screen.findByText(/bell pepper \(model: capsicum\)/i);
    await screen.findByText(/orange \(model: oren\)/i);

    const checkboxes = scanPanel.getAllByRole("checkbox");
    expect(checkboxes[0]).toBeChecked();
    expect(checkboxes[1]).not.toBeChecked();
    expect(checkboxes[1]).toBeDisabled();

    await user.click(scanPanel.getByRole("button", { name: "Add selected to inventory" }));

    const inventoryPanel = getPanel("Inventory Editor");
    await inventoryPanel.findByText("bell pepper");
    expect(inventoryPanel.queryByText("orange")).not.toBeInTheDocument();
    expect(scanPanel.getByText(/Only supported detections are confirmable in v1/i)).toBeInTheDocument();
  });

  it("keeps inventory editing working after a demo scenario load", async () => {
    const { user } = await renderDashboard([
      buildInventoryItem(1, "egg", 2, "item", "protein")
    ]);

    const demoPanel = getPanel("Scenario Loader");
    await user.selectOptions(demoPanel.getByRole("combobox"), "veggie_reset");
    await user.click(demoPanel.getByRole("button", { name: "Load scenario" }));

    const inventoryPanel = getPanel("Inventory Editor");
    await inventoryPanel.findByText("rice");
    await user.click(getInventoryRow("rice").getByRole("button", { name: "Edit" }));

    const ingredientInput = inventoryPanel.getByPlaceholderText("ingredient");
    await user.clear(ingredientInput);
    await user.type(ingredientInput, "Brown Rice");
    await user.click(inventoryPanel.getByRole("button", { name: "Update item" }));

    await inventoryPanel.findByText("brown rice");
    expect(inventoryPanel.queryByText("rice")).not.toBeInTheDocument();
  });
});
