// -------------------------------------------------------------------------
// Shared TypeScript types — mirrors backend Pydantic schemas
// -------------------------------------------------------------------------

export type SourceType =
  | "university"
  | "company"
  | "news"
  | "personal"
  | "local_news"
  | "rss";

export interface Lead {
  id: number;
  date: string; // ISO date string "YYYY-MM-DD"
  rank: number; // 1, 2, or 3
  name: string;
  title: string;
  affiliation: string;
  url: string;
  summary: string;
  source_type: SourceType;
  contact_hint: string | null;
  favorited: boolean;
  vote: -1 | 0 | 1;
  matched_interests: number[];
  created_at: string; // ISO datetime string
}

export interface InterestConfig {
  id: number;
  keyword: string;
  weight: number; // 0.0 – 1.0
  active: boolean;
  created_at: string;
}

export interface ScraperSource {
  id: number;
  name: string;
  scraper_class: string;
  config: string; // JSON string
  enabled: boolean;
  last_run_at: string | null;
  last_run_status: "success" | "error" | "skipped" | null;
}

// Generic paginated list response shape: { items: T[], total: number }
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

// -------------------------------------------------------------------------
// Request / partial types for mutations
// -------------------------------------------------------------------------

export interface CreateInterestPayload {
  keyword: string;
  weight?: number;
  active?: boolean;
}

export interface UpdateInterestPayload {
  keyword?: string;
  weight?: number;
  active?: boolean;
}

export interface CreateSourcePayload {
  name: string;
  scraper_class: string;
  config: string;
  enabled?: boolean;
}

export interface UpdateSourcePayload {
  name?: string;
  scraper_class?: string;
  config?: string;
  enabled?: boolean;
}

export interface VotePayload {
  vote: -1 | 0 | 1;
}

export interface FavoritePayload {
  favorited: boolean;
}

export interface ParseInterestPayload {
  text: string;
}

export interface ParseInterestResponse {
  created: InterestConfig[];
  skipped: string[];
}
