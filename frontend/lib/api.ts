import type {
  BackendHealth,
  DailyCalorieSummary,
  DemoScenarioSummary,
  DemoSnapshot,
  InventoryItem,
  MetadataResponse,
  Recommendation,
  Recipe,
  ScanConfirmationResponse,
  ScanResult,
  ShoppingList,
  UserProfile
} from "@/lib/types";

function resolveApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!configured || configured === "http://127.0.0.1:8000" || configured === "http://localhost:8000") {
    return "/api/backend";
  }
  return configured;
}

const API_BASE_URL = resolveApiBaseUrl();

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const fallbackMessage = `Request failed with status ${response.status}`;
    let message = fallbackMessage;
    try {
      const payload = (await response.json()) as { detail?: string; error?: { message?: string } };
      if (payload.detail) {
        message = payload.detail;
      } else if (payload.error?.message) {
        message = payload.error.message;
      }
    } catch {
      message = fallbackMessage;
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function fetchProfile() {
  return request<UserProfile>("/profile");
}

export async function fetchBackendHealth() {
  return request<BackendHealth>("/health");
}

export async function updateProfile(payload: Partial<UserProfile>) {
  return request<UserProfile>("/profile", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function fetchInventory() {
  return request<InventoryItem[]>("/inventory");
}

export async function createInventoryItem(payload: Partial<InventoryItem> & { name: string }) {
  return request<InventoryItem>("/inventory", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateInventoryItem(itemId: number, payload: Partial<InventoryItem>) {
  return request<InventoryItem>(`/inventory/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteInventoryItem(itemId: number) {
  return request<void>(`/inventory/${itemId}`, {
    method: "DELETE"
  });
}

export async function fetchRecipes() {
  return request<Recipe[]>("/recipes");
}

export async function fetchMetadata() {
  return request<MetadataResponse>("/metadata");
}

export async function fetchCalories() {
  return request<DailyCalorieSummary>("/calories/today");
}

export async function updateCalories(payload: Pick<DailyCalorieSummary, "consumed" | "burned">) {
  return request<DailyCalorieSummary>("/calories/today", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function fetchRecommendations(limit = 4) {
  return request<Recommendation[]>(`/recommendations?limit=${limit}`);
}

export async function fetchShoppingList(recipeIds: number[] = [], topN = 1) {
  const params = new URLSearchParams({ top_n: String(topN) });
  if (recipeIds.length) {
    params.set("recipe_ids", recipeIds.join(","));
  }
  return request<ShoppingList>(`/shopping-list?${params.toString()}`);
}

export async function createScan(imageName: string) {
  return request<ScanResult>("/scan", {
    method: "POST",
    body: JSON.stringify({ image_name: imageName })
  });
}

export async function uploadScanImage(file: File, imageName?: string) {
  const formData = new FormData();
  formData.append("image", file);
  formData.append("image_name", imageName || file.name);

  const response = await fetch(`${API_BASE_URL}/scan`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    const fallbackMessage = `Request failed with status ${response.status}`;
    let message = fallbackMessage;
    try {
      const payload = (await response.json()) as { detail?: string; error?: { message?: string } };
      if (payload.detail) {
        message = payload.detail;
      } else if (payload.error?.message) {
        message = payload.error.message;
      }
    } catch {
      message = fallbackMessage;
    }
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as ScanResult;
}

export async function confirmScan(sessionId: string, acceptedIngredients: string[]) {
  return request<ScanConfirmationResponse>(`/scan/confirm?session_id=${encodeURIComponent(sessionId)}`, {
    method: "POST",
    body: JSON.stringify({ accepted_ingredients: acceptedIngredients })
  });
}

export async function fetchDemoScenarios() {
  return request<DemoScenarioSummary[]>("/demo/scenarios");
}

export async function resetDemoState() {
  return request<DemoSnapshot>("/demo/reset", {
    method: "POST"
  });
}

export async function loadDemoScenario(scenarioId: string) {
  return request<DemoSnapshot>(`/demo/load/${encodeURIComponent(scenarioId)}`, {
    method: "POST"
  });
}

export { ApiError, API_BASE_URL };
