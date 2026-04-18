import type { InventoryItem } from "@/lib/types";

const DEFAULT_UNIT = "item";
const DEFAULT_CATEGORY = "pantry";
const DEFAULT_SOURCE = "manual";

export interface InventoryMutationInput {
  name: string;
  quantity: number | string;
  unit: string;
  category: string;
}

export interface InventoryMutationPayload {
  name: string;
  quantity: number;
  unit: string;
  category: string;
}

function normalizeText(value: string, fallback: string) {
  const normalized = value.trim().toLowerCase();
  return normalized || fallback;
}

export function normalizeInventoryItem(item: InventoryItem): InventoryItem {
  return {
    ...item,
    name: item.name.trim().toLowerCase(),
    unit: normalizeText(item.unit, DEFAULT_UNIT),
    category: normalizeText(item.category, DEFAULT_CATEGORY),
    source: normalizeText(item.source, DEFAULT_SOURCE)
  };
}

export function normalizeInventorySnapshot(items: InventoryItem[]) {
  return [...items]
    .map((item) => normalizeInventoryItem(item))
    .sort((left, right) => left.name.localeCompare(right.name));
}

export function upsertInventoryItemInSnapshot(items: InventoryItem[], item: InventoryItem) {
  const normalized = normalizeInventoryItem(item);
  const nextItems = items.filter((existing) => existing.id !== normalized.id);
  nextItems.push(normalized);
  return normalizeInventorySnapshot(nextItems);
}

export function mergeInventoryItemsIntoSnapshot(items: InventoryItem[], nextItems: InventoryItem[]) {
  return nextItems.reduce((current, item) => upsertInventoryItemInSnapshot(current, item), items);
}

export function removeInventoryItemFromSnapshot(items: InventoryItem[], itemId: number) {
  return normalizeInventorySnapshot(items.filter((item) => item.id !== itemId));
}

export function buildInventoryMutationPayload(input: InventoryMutationInput): InventoryMutationPayload {
  const name = input.name.trim().toLowerCase();
  const quantity = typeof input.quantity === "number" ? input.quantity : Number(input.quantity);
  const unit = normalizeText(input.unit, DEFAULT_UNIT);
  const category = normalizeText(input.category, DEFAULT_CATEGORY);

  if (!name) {
    throw new Error("Enter an ingredient name before adding it.");
  }

  if (!Number.isFinite(quantity) || quantity <= 0) {
    throw new Error("Enter a quantity greater than 0.");
  }

  return { name, quantity, unit, category };
}
