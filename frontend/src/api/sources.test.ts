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
  createSource,
  deleteSource,
  getSourceById,
  getSources,
  toggleSource,
  updateSource,
} from "./sources";
import type { ScraperSource } from "../types";

const mockSource: ScraperSource = {
  id: 1,
  name: "MIT Faculty Directory",
  scraper_class: "app.scrapers.university.UniversityScraper",
  config: "{}",
  enabled: true,
  last_run_at: null,
  last_run_status: null,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getSources", () => {
  it("fetches paginated list", async () => {
    vi.mocked(client.get).mockResolvedValue({
      data: { items: [mockSource], total: 1 },
    });
    const result = await getSources();
    expect(client.get).toHaveBeenCalledWith("/api/v1/sources");
    expect(result.items).toEqual([mockSource]);
  });
});

describe("getSourceById", () => {
  it("fetches by ID", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockSource });
    const result = await getSourceById(1);
    expect(client.get).toHaveBeenCalledWith("/api/v1/sources/1");
    expect(result).toEqual(mockSource);
  });
});

describe("createSource", () => {
  it("posts with payload and returns created source", async () => {
    vi.mocked(client.post).mockResolvedValue({ data: mockSource });
    const result = await createSource({
      name: "MIT Faculty Directory",
      scraper_class: "app.scrapers.university.UniversityScraper",
      config: "{}",
    });
    expect(client.post).toHaveBeenCalledWith("/api/v1/sources", expect.objectContaining({
      name: "MIT Faculty Directory",
    }));
    expect(result).toEqual(mockSource);
  });
});

describe("updateSource", () => {
  it("patches with partial payload", async () => {
    const updated = { ...mockSource, enabled: false };
    vi.mocked(client.patch).mockResolvedValue({ data: updated });
    const result = await updateSource(1, { enabled: false });
    expect(client.patch).toHaveBeenCalledWith("/api/v1/sources/1", { enabled: false });
    expect(result).toEqual(updated);
  });
});

describe("toggleSource", () => {
  it("patches enabled=true via updateSource", async () => {
    const updated = { ...mockSource, enabled: true };
    vi.mocked(client.patch).mockResolvedValue({ data: updated });
    const result = await toggleSource(1, true);
    expect(client.patch).toHaveBeenCalledWith("/api/v1/sources/1", { enabled: true });
    expect(result.enabled).toBe(true);
  });

  it("patches enabled=false via updateSource", async () => {
    const updated = { ...mockSource, enabled: false };
    vi.mocked(client.patch).mockResolvedValue({ data: updated });
    await toggleSource(1, false);
    expect(client.patch).toHaveBeenCalledWith("/api/v1/sources/1", { enabled: false });
  });
});

describe("deleteSource", () => {
  it("sends DELETE request", async () => {
    vi.mocked(client.delete).mockResolvedValue({ data: undefined });
    await deleteSource(1);
    expect(client.delete).toHaveBeenCalledWith("/api/v1/sources/1");
  });
});
