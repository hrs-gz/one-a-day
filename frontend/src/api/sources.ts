import type {
  CreateSourcePayload,
  PaginatedResponse,
  ScraperSource,
  UpdateSourcePayload,
} from "../types";
import { client } from "./client";

const BASE = "/api/v1/sources";

export async function getSources(): Promise<PaginatedResponse<ScraperSource>> {
  const { data } = await client.get<PaginatedResponse<ScraperSource>>(BASE);
  return data;
}

export async function getSourceById(id: number): Promise<ScraperSource> {
  const { data } = await client.get<ScraperSource>(`${BASE}/${id}`);
  return data;
}

export async function createSource(payload: CreateSourcePayload): Promise<ScraperSource> {
  const { data } = await client.post<ScraperSource>(BASE, payload);
  return data;
}

export async function updateSource(
  id: number,
  payload: UpdateSourcePayload
): Promise<ScraperSource> {
  const { data } = await client.patch<ScraperSource>(`${BASE}/${id}`, payload);
  return data;
}

export async function toggleSource(id: number, enabled: boolean): Promise<ScraperSource> {
  return updateSource(id, { enabled });
}

export async function deleteSource(id: number): Promise<void> {
  await client.delete(`${BASE}/${id}`);
}
