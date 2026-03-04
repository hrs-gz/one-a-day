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
  createInterest,
  deleteInterest,
  getInterestById,
  getInterests,
  parseInterests,
  updateInterest,
} from "./interests";
import type { InterestConfig } from "../types";

const mockInterest: InterestConfig = {
  id: 1,
  keyword: "urban planning",
  weight: 0.8,
  active: true,
  created_at: "2025-03-01T00:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getInterests", () => {
  it("fetches paginated list", async () => {
    vi.mocked(client.get).mockResolvedValue({
      data: { items: [mockInterest], total: 1 },
    });
    const result = await getInterests();
    expect(client.get).toHaveBeenCalledWith("/api/v1/interests");
    expect(result.items).toEqual([mockInterest]);
    expect(result.total).toBe(1);
  });
});

describe("getInterestById", () => {
  it("fetches by ID", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockInterest });
    const result = await getInterestById(1);
    expect(client.get).toHaveBeenCalledWith("/api/v1/interests/1");
    expect(result).toEqual(mockInterest);
  });
});

describe("createInterest", () => {
  it("posts with payload and returns created interest", async () => {
    vi.mocked(client.post).mockResolvedValue({ data: mockInterest });
    const result = await createInterest({ keyword: "urban planning", weight: 0.8 });
    expect(client.post).toHaveBeenCalledWith("/api/v1/interests", {
      keyword: "urban planning",
      weight: 0.8,
    });
    expect(result).toEqual(mockInterest);
  });
});

describe("updateInterest", () => {
  it("patches with partial payload", async () => {
    const updated = { ...mockInterest, weight: 0.5 };
    vi.mocked(client.patch).mockResolvedValue({ data: updated });
    const result = await updateInterest(1, { weight: 0.5 });
    expect(client.patch).toHaveBeenCalledWith("/api/v1/interests/1", { weight: 0.5 });
    expect(result).toEqual(updated);
  });
});

describe("deleteInterest", () => {
  it("sends DELETE request", async () => {
    vi.mocked(client.delete).mockResolvedValue({ data: undefined });
    await deleteInterest(1);
    expect(client.delete).toHaveBeenCalledWith("/api/v1/interests/1");
  });
});

describe("parseInterests", () => {
  it("posts text and returns created/skipped", async () => {
    vi.mocked(client.post).mockResolvedValue({
      data: { created: [mockInterest], skipped: ["city planning"] },
    });
    const result = await parseInterests({ text: "urban planning, city planning" });
    expect(client.post).toHaveBeenCalledWith("/api/v1/interests/parse", {
      text: "urban planning, city planning",
    });
    expect(result.created).toHaveLength(1);
    expect(result.skipped).toEqual(["city planning"]);
  });
});
