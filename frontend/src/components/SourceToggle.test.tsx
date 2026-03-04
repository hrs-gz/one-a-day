import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../hooks/useInterests", () => ({
  useSources: vi.fn(),
  useToggleSource: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("../utils/date", () => ({
  formatDate: (d: string) => d,
}));

import { useSources, useToggleSource } from "../hooks/useInterests";
import type { ScraperSource } from "../types";
import { SourceToggle } from "./SourceToggle";

const mockSource: ScraperSource = {
  id: 1,
  name: "MIT Faculty Directory",
  scraper_class: "app.scrapers.university.UniversityScraper",
  config: "{}",
  enabled: true,
  last_run_at: null,
  last_run_status: null,
};

type MockQueryResult = {
  data: { items: ScraperSource[]; total: number } | undefined;
  isLoading: boolean;
  isError: boolean;
};

function mockUseSources(value: MockQueryResult) {
  vi.mocked(useSources).mockReturnValue(
    value as unknown as ReturnType<typeof useSources>
  );
}

describe("SourceToggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading text while fetching", () => {
    mockUseSources({ data: undefined, isLoading: true, isError: false });
    render(<SourceToggle />);
    expect(screen.getByText("Loading sources…")).toBeInTheDocument();
  });

  it("shows error message on fetch failure", () => {
    mockUseSources({ data: undefined, isLoading: false, isError: true });
    render(<SourceToggle />);
    expect(screen.getByText("Failed to load sources.")).toBeInTheDocument();
  });

  it("shows empty-state when no sources configured", () => {
    mockUseSources({ data: { items: [], total: 0 }, isLoading: false, isError: false });
    render(<SourceToggle />);
    expect(screen.getByText("No scraper sources configured.")).toBeInTheDocument();
  });

  it("renders source name and 'Never run' when last_run_at is null", () => {
    mockUseSources({
      data: { items: [mockSource], total: 1 },
      isLoading: false,
      isError: false,
    });
    render(<SourceToggle />);
    expect(screen.getByText("MIT Faculty Directory")).toBeInTheDocument();
    expect(screen.getByText("Never run")).toBeInTheDocument();
  });

  it("renders checked checkbox when source is enabled", () => {
    mockUseSources({
      data: { items: [mockSource], total: 1 },
      isLoading: false,
      isError: false,
    });
    render(<SourceToggle />);
    const checkbox = screen.getByRole("checkbox", { name: /Toggle MIT Faculty Directory/i });
    expect(checkbox).toBeChecked();
  });

  it("calls toggleMutation.mutate with toggled enabled value on checkbox change", async () => {
    const mockMutate = vi.fn();
    vi.mocked(useToggleSource).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useToggleSource>);
    mockUseSources({
      data: { items: [mockSource], total: 1 },
      isLoading: false,
      isError: false,
    });
    const user = userEvent.setup();
    render(<SourceToggle />);
    await user.click(screen.getByRole("checkbox", { name: /Toggle MIT Faculty Directory/i }));
    expect(mockMutate).toHaveBeenCalledWith({ id: 1, enabled: false });
  });

  it("shows status badge for last run result", () => {
    const sourceWithRun: ScraperSource = {
      ...mockSource,
      last_run_at: "2025-03-01T06:00:00Z",
      last_run_status: "success",
    };
    mockUseSources({
      data: { items: [sourceWithRun], total: 1 },
      isLoading: false,
      isError: false,
    });
    render(<SourceToggle />);
    expect(screen.getByText("success")).toBeInTheDocument();
  });
});
