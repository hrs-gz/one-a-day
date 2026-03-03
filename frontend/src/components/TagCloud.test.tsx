import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../hooks/useInterests", () => ({
  useUpdateInterest: vi.fn(() => ({ mutate: vi.fn() })),
  useDeleteInterest: vi.fn(() => ({ mutate: vi.fn() })),
}));

import { useDeleteInterest, useUpdateInterest } from "../hooks/useInterests";
import type { InterestConfig } from "../types";
import { TagCloud } from "./TagCloud";

const mockInterests: InterestConfig[] = [
  { id: 1, keyword: "urban planning", weight: 0.8, active: true, created_at: "2025-03-01T00:00:00Z" },
  { id: 2, keyword: "marine biology", weight: 0.4, active: false, created_at: "2025-03-01T00:00:00Z" },
];

describe("TagCloud", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty-state message when no interests", () => {
    render(<TagCloud interests={[]} />);
    expect(screen.getByText(/No interests yet/)).toBeInTheDocument();
  });

  it("renders a chip for each interest", () => {
    render(<TagCloud interests={mockInterests} />);
    expect(screen.getByText("urban planning")).toBeInTheDocument();
    expect(screen.getByText("marine biology")).toBeInTheDocument();
  });

  it("opens the editor when a chip is clicked", async () => {
    const user = userEvent.setup();
    render(<TagCloud interests={mockInterests} />);
    await user.click(screen.getByText("urban planning"));
    // Editor renders a weight slider and Save / Delete / ✕ buttons
    expect(screen.getByRole("slider")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
  });

  it("calls updateMutation.mutate when Save is clicked", async () => {
    const mockMutate = vi.fn();
    vi.mocked(useUpdateInterest).mockReturnValue({ mutate: mockMutate } as unknown as ReturnType<typeof useUpdateInterest>);
    const user = userEvent.setup();
    render(<TagCloud interests={mockInterests} />);
    await user.click(screen.getByText("urban planning"));
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(mockMutate).toHaveBeenCalledWith(
      { id: 1, payload: { weight: 0.8 } },
      expect.anything()
    );
  });

  it("calls deleteMutation.mutate when Delete is clicked", async () => {
    const mockMutate = vi.fn();
    vi.mocked(useDeleteInterest).mockReturnValue({ mutate: mockMutate } as unknown as ReturnType<typeof useDeleteInterest>);
    const user = userEvent.setup();
    render(<TagCloud interests={mockInterests} />);
    await user.click(screen.getByText("urban planning"));
    await user.click(screen.getByRole("button", { name: /delete/i }));
    expect(mockMutate).toHaveBeenCalledWith(1, expect.anything());
  });

  it("closes the editor when ✕ is clicked", async () => {
    const user = userEvent.setup();
    render(<TagCloud interests={mockInterests} />);
    await user.click(screen.getByText("urban planning"));
    expect(screen.getByRole("slider")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "✕" }));
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  });
});
