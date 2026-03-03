import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./client", () => ({
  client: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { client } from "./client";
import {
  favoriteLead,
  generateLead,
  getLeadById,
  getLeads,
  getLeadsByDate,
  getTodayLead,
  voteOnLead,
} from "./leads";
import type { Lead } from "../types";

const mockLead: Lead = {
  id: 1,
  date: "2025-03-01",
  rank: 1,
  name: "Dr. Jane Smith",
  title: "Associate Professor",
  affiliation: "MIT",
  url: "https://mit.edu/faculty/jsmith",
  summary: "Researches urban planning.",
  source_type: "university",
  contact_hint: null,
  favorited: false,
  vote: 0,
  matched_interests: [],
  created_at: "2025-03-01T06:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getTodayLead", () => {
  it("returns a lead on success", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockLead });
    const result = await getTodayLead();
    expect(client.get).toHaveBeenCalledWith("/api/v1/leads/today");
    expect(result).toEqual(mockLead);
  });

  it("returns null on 404", async () => {
    vi.mocked(client.get).mockRejectedValue({ response: { status: 404 } });
    const result = await getTodayLead();
    expect(result).toBeNull();
  });

  it("rethrows non-404 errors", async () => {
    vi.mocked(client.get).mockRejectedValue(new Error("Network error"));
    await expect(getTodayLead()).rejects.toThrow("Network error");
  });
});

describe("getLeads", () => {
  it("calls correct endpoint with default pagination", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: { items: [mockLead], total: 1 } });
    await getLeads();
    expect(client.get).toHaveBeenCalledWith("/api/v1/leads", {
      params: { skip: 0, limit: 20 },
    });
  });

  it("calculates skip from page number", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: { items: [], total: 0 } });
    await getLeads(3, 10);
    expect(client.get).toHaveBeenCalledWith("/api/v1/leads", {
      params: { skip: 20, limit: 10 },
    });
  });

  it("includes source_type param when provided", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: { items: [], total: 0 } });
    await getLeads(1, 20, "university");
    expect(client.get).toHaveBeenCalledWith("/api/v1/leads", {
      params: { skip: 0, limit: 20, source_type: "university" },
    });
  });
});

describe("getLeadById", () => {
  it("fetches by ID", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockLead });
    const result = await getLeadById(1);
    expect(client.get).toHaveBeenCalledWith("/api/v1/leads/1");
    expect(result).toEqual(mockLead);
  });
});

describe("getLeadsByDate", () => {
  it("fetches leads for a date", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: [mockLead] });
    const result = await getLeadsByDate("2025-03-01");
    expect(client.get).toHaveBeenCalledWith("/api/v1/leads/by-date/2025-03-01");
    expect(result).toEqual([mockLead]);
  });
});

describe("generateLead", () => {
  it("posts to generate endpoint and returns lead array", async () => {
    vi.mocked(client.post).mockResolvedValue({ data: [mockLead] });
    const result = await generateLead();
    expect(client.post).toHaveBeenCalledWith("/api/v1/leads/generate");
    expect(result).toEqual([mockLead]);
  });
});

describe("voteOnLead", () => {
  it("patches vote endpoint with payload", async () => {
    const updated = { ...mockLead, vote: 1 as const };
    vi.mocked(client.patch).mockResolvedValue({ data: updated });
    const result = await voteOnLead(1, { vote: 1 });
    expect(client.patch).toHaveBeenCalledWith("/api/v1/leads/1/vote", { vote: 1 });
    expect(result).toEqual(updated);
  });
});

describe("favoriteLead", () => {
  it("patches favorite endpoint with payload", async () => {
    const updated = { ...mockLead, favorited: true };
    vi.mocked(client.patch).mockResolvedValue({ data: updated });
    const result = await favoriteLead(1, { favorited: true });
    expect(client.patch).toHaveBeenCalledWith("/api/v1/leads/1/favorite", { favorited: true });
    expect(result).toEqual(updated);
  });
});
