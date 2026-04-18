export type DietaryPreference = "omnivore" | "vegetarian" | "vegan" | "pescatarian";
export type HealthGoal = "weight_loss" | "maintenance" | "muscle_gain";

export interface UserProfile {
  id: number;
  name: string;
  dietary_preference: DietaryPreference;
  allergens: string[];
  health_goal: HealthGoal;
  calorie_target: number;
  preference_tags: string[];
}

export interface InventoryItem {
  id: number;
  name: string;
  quantity: number;
  unit: string;
  category: string;
  source: string;
  confidence: number | null;
  last_updated: string;
}

export interface RecipeIngredient {
  name: string;
  quantity: number;
  unit: string;
  category: string;
  optional: boolean;
}

export interface Recipe {
  id: number;
  title: string;
  description: string;
  dietary_tags: string[];
  allergens: string[];
  preference_tags: string[];
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  prep_minutes: number;
  instructions: string[];
  ingredients: RecipeIngredient[];
}

export interface DailyCalorieSummary {
  date: string;
  consumed: number;
  burned: number;
}

export interface Detection {
  ingredient_name: string;
  model_label: string;
  confidence: number;
  category: string;
  quantity: number;
  unit: string;
  supported: boolean;
}

export interface ScanResult {
  session_id: string;
  image_name: string;
  detections: Detection[];
  created_at: string;
  image_mime_type: string | null;
  image_size_bytes: number | null;
  image_url: string | null;
  detector: string;
  model_name: string | null;
  confidence_threshold: number | null;
}

export interface Recommendation {
  recipe_id: number;
  recipe_title: string;
  score: number;
  explanation: string;
  ingredient_match_ratio: number;
  missing_items_ratio: number;
  health_goal_alignment: number;
  user_preference_match: number;
  calorie_fit_score: number;
  protein_fit_score: number;
  macro_balance_score: number;
  narrative_style: string;
  matched_ingredients: string[];
  missing_ingredients: string[];
}

export interface ShoppingListItem {
  name: string;
  category: string;
  quantity: number;
  unit: string;
}

export type ShoppingList = Record<string, ShoppingListItem[]>;

export interface MetadataBucketItem {
  value: string;
  description: string;
  sort_order: number;
}

export type MetadataResponse = Record<string, MetadataBucketItem[]>;

export interface ScanConfirmationResponse {
  scan_result: ScanResult;
  accepted: Detection[];
  inventory_updates: InventoryItem[];
}

export interface DemoScenarioSummary {
  id: string;
  name: string;
  description: string;
}

export interface DemoSnapshot {
  profile: UserProfile;
  inventory: InventoryItem[];
  calories: DailyCalorieSummary;
  recommendations: Recommendation[];
  active_scenario?: DemoScenarioSummary;
}

export interface BackendHealth {
  status: string;
  version: string;
  detector_requested: string;
  detector_active: string;
  detector_warning: string | null;
  max_upload_size_bytes: number;
}
