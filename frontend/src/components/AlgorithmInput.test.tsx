import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/interests", () => ({
  parseInterests: vi.fn(),
}));

import { parseInterests } from "../api/interests";
import { AlgorithmInput } from "./AlgorithmInput";

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const mockInterest = {
  id: 1,
  keyword: "urban planning",
  weight: 1.0,
  active: true,
  created_at: "2025-03-01T00:00:00Z",
};

describe("AlgorithmInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders textarea and a disabled submit button when empty", () => {
    render(<AlgorithmInput />, { wrapper: Wrapper });
    expect(
      screen.getByPlaceholderText("What would you like to know?")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Submit")).toBeDisabled();
  });

  it("enables submit when text is entered", async () => {
    const user = userEvent.setup();
    render(<AlgorithmInput />, { wrapper: Wrapper });
    await user.type(screen.getByRole("textbox"), "urban planning");
    expect(screen.getByLabelText("Submit")).not.toBeDisabled();
  });

  it("calls parseInterests and shows success feedback with count", async () => {
    vi.mocked(parseInterests).mockResolvedValue({
      created: [mockInterest],
      skipped: [],
    });
    const user = userEvent.setup();
    render(<AlgorithmInput />, { wrapper: Wrapper });
    await user.type(screen.getByRole("textbox"), "urban planning");
    await user.click(screen.getByLabelText("Submit"));
    await waitFor(() =>
      expect(screen.getByText(/Added 1 keyword/)).toBeInTheDocument()
    );
    expect(parseInterests).toHaveBeenCalledWith({ text: "urban planning" });
  });

  it("reports skipped duplicates alongside added keywords", async () => {
    vi.mocked(parseInterests).mockResolvedValue({
      created: [mockInterest],
      skipped: ["city planning"],
    });
    const user = userEvent.setup();
    render(<AlgorithmInput />, { wrapper: Wrapper });
    await user.type(screen.getByRole("textbox"), "urban planning, city planning");
    await user.click(screen.getByLabelText("Submit"));
    await waitFor(() =>
      expect(screen.getByText(/skipped 1 duplicate/)).toBeInTheDocument()
    );
  });

  it("shows 'no new keywords' when all already exist", async () => {
    vi.mocked(parseInterests).mockResolvedValue({
      created: [],
      skipped: ["urban planning"],
    });
    const user = userEvent.setup();
    render(<AlgorithmInput />, { wrapper: Wrapper });
    await user.type(screen.getByRole("textbox"), "urban planning");
    await user.click(screen.getByLabelText("Submit"));
    await waitFor(() =>
      expect(screen.getByText(/No new keywords/)).toBeInTheDocument()
    );
  });

  it("shows error feedback on API failure", async () => {
    vi.mocked(parseInterests).mockRejectedValue(new Error("Network error"));
    const user = userEvent.setup();
    render(<AlgorithmInput />, { wrapper: Wrapper });
    await user.type(screen.getByRole("textbox"), "some topic");
    await user.click(screen.getByLabelText("Submit"));
    await waitFor(() =>
      expect(
        screen.getByText("Something went wrong. Try again.")
      ).toBeInTheDocument()
    );
  });

  it("submits on Ctrl+Enter", async () => {
    vi.mocked(parseInterests).mockResolvedValue({ created: [], skipped: [] });
    const user = userEvent.setup();
    render(<AlgorithmInput />, { wrapper: Wrapper });
    await user.type(screen.getByRole("textbox"), "test topic");
    await user.keyboard("{Control>}{Enter}{/Control}");
    expect(parseInterests).toHaveBeenCalledWith({ text: "test topic" });
  });

  it("clears textarea after successful submit", async () => {
    vi.mocked(parseInterests).mockResolvedValue({
      created: [mockInterest],
      skipped: [],
    });
    const user = userEvent.setup();
    render(<AlgorithmInput />, { wrapper: Wrapper });
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "urban planning");
    await user.click(screen.getByLabelText("Submit"));
    await waitFor(() => expect(textarea).toHaveValue(""));
  });
});
