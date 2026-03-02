import type { FavoritePayload, Lead, PaginatedResponse, VotePayload } from "../types";
import { client } from "./client";

const BASE = "/api/v1/leads";

/**
 * Fetch today's lead. Returns null (404) if no lead has been generated yet.
 */
export async function getTodayLead(): Promise<Lead | null> {
  try {
    const { data } = await client.get<Lead>(`${BASE}/today`);
    return data;
  } catch (err: unknown) {
    // Treat 404 as "no lead today" — not an error state
    if (axios404(err)) return null;
    throw err;
  }
}

/**
 * Fetch a paginated list of past leads.
 * @param page  1-based page number (default 1)
 * @param limit Items per page (default 20)
 * @param sourceType Optional filter by source_type
 */
export async function getLeads(
  page = 1,
  limit = 20,
  sourceType?: string
): Promise<PaginatedResponse<Lead>> {
  const params: Record<string, string | number> = {
    skip: (page - 1) * limit,
    limit,
  };
  if (sourceType) params.source_type = sourceType;

  const { data } = await client.get<PaginatedResponse<Lead>>(BASE, { params });
  return data;
}

/**
 * Fetch a single lead by ID.
 */
export async function getLeadById(id: number): Promise<Lead> {
  const { data } = await client.get<Lead>(`${BASE}/${id}`);
  return data;
}

/**
 * Trigger the full scrape + score + select pipeline for today.
 * Returns up to 3 newly created leads.
 */
export async function generateLead(): Promise<Lead[]> {
  const { data } = await client.post<Lead[]>(`${BASE}/generate`);
  return data;
}

/**
 * Fetch all leads for a given calendar date (YYYY-MM-DD).
 * Returns an empty array if no leads exist for that date.
 */
export async function getLeadsByDate(date: string): Promise<Lead[]> {
  const { data } = await client.get<Lead[]>(`${BASE}/by-date/${date}`);
  return data;
}

/**
 * Vote on a lead (-1 downvote, 0 neutral, +1 upvote).
 */
export async function voteOnLead(id: number, payload: VotePayload): Promise<Lead> {
  const { data } = await client.patch<Lead>(`${BASE}/${id}/vote`, payload);
  return data;
}

/**
 * Toggle the favorited state of a lead.
 */
export async function favoriteLead(id: number, payload: FavoritePayload): Promise<Lead> {
  const { data } = await client.patch<Lead>(`${BASE}/${id}/favorite`, payload);
  return data;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function axios404(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "response" in err &&
    (err as { response?: { status?: number } }).response?.status === 404
  );
}
