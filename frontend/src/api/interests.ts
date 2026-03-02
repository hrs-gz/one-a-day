import type {
  CreateInterestPayload,
  InterestConfig,
  PaginatedResponse,
  UpdateInterestPayload,
} from "../types";
import { client } from "./client";

const BASE = "/api/v1/interests";

export async function getInterests(): Promise<PaginatedResponse<InterestConfig>> {
  const { data } = await client.get<PaginatedResponse<InterestConfig>>(BASE);
  return data;
}

export async function getInterestById(id: number): Promise<InterestConfig> {
  const { data } = await client.get<InterestConfig>(`${BASE}/${id}`);
  return data;
}

export async function createInterest(payload: CreateInterestPayload): Promise<InterestConfig> {
  const { data } = await client.post<InterestConfig>(BASE, payload);
  return data;
}

export async function updateInterest(
  id: number,
  payload: UpdateInterestPayload
): Promise<InterestConfig> {
  const { data } = await client.patch<InterestConfig>(`${BASE}/${id}`, payload);
  return data;
}

export async function deleteInterest(id: number): Promise<void> {
  await client.delete(`${BASE}/${id}`);
}

export async function parseInterests(
  payload: { text: string }
): Promise<{ created: { id: number; keyword: string; weight: number; active: boolean; created_at: string }[]; skipped: string[] }> {
  const { data } = await client.post(`${BASE}/parse`, payload);
  return data;
}
