import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Lead } from "../types";
import { LeadCard } from "./LeadCard";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

const mockLead: Lead = {
  id: 1,
  date: "2025-03-01",
  rank: 1,
  name: "Dr. Jane Smith",
  title: "Associate Professor",
  affiliation: "MIT",
  url: "https://mit.edu/faculty/jsmith",
  summary: "Researches urban planning and sustainable cities.",
  source_type: "university",
  contact_hint: "https://linkedin.com/in/jsmith",
  favorited: false,
  vote: 0,
  matched_interests: [],
  created_at: "2025-03-01T06:00:00Z",
};

const DATE = "2025-03-01";

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("LeadCard", () => {
  it("renders name, title and affiliation", () => {
    render(<LeadCard lead={mockLead} date={DATE} />, { wrapper: makeWrapper() });

    expect(screen.getByText("Dr. Jane Smith")).toBeInTheDocument();
    expect(screen.getByText(/Associate Professor/)).toBeInTheDocument();
    expect(screen.getByText(/MIT/)).toBeInTheDocument();
  });

  it("renders source type link", () => {
    render(<LeadCard lead={mockLead} date={DATE} />, { wrapper: makeWrapper() });
    const link = screen.getByRole("link", { name: "university" });
    expect(link).toHaveAttribute("href", "https://mit.edu/faculty/jsmith");
  });

  it("renders contact link when contact_hint is present", () => {
    render(<LeadCard lead={mockLead} date={DATE} />, { wrapper: makeWrapper() });
    const link = screen.getByRole("link", { name: /contact/i });
    expect(link).toHaveAttribute("href", "https://linkedin.com/in/jsmith");
  });

  it("does not render contact link when contact_hint is null", () => {
    const leadNoContact: Lead = { ...mockLead, contact_hint: null };
    render(<LeadCard lead={leadNoContact} date={DATE} />, { wrapper: makeWrapper() });
    expect(screen.queryByRole("link", { name: /contact/i })).not.toBeInTheDocument();
  });

  it("formats email contact_hint as mailto link", () => {
    const leadEmail: Lead = { ...mockLead, contact_hint: "jane@mit.edu" };
    render(<LeadCard lead={leadEmail} date={DATE} />, { wrapper: makeWrapper() });
    const link = screen.getByRole("link", { name: /contact/i });
    expect(link).toHaveAttribute("href", "mailto:jane@mit.edu");
  });

  it("shows filled star when favorited", () => {
    const favLead: Lead = { ...mockLead, favorited: true };
    render(<LeadCard lead={favLead} date={DATE} />, { wrapper: makeWrapper() });
    expect(screen.getByLabelText(/remove from favorites/i)).toBeInTheDocument();
  });

  it("shows empty star when not favorited", () => {
    render(<LeadCard lead={mockLead} date={DATE} />, { wrapper: makeWrapper() });
    expect(screen.getByLabelText(/add to favorites/i)).toBeInTheDocument();
  });
});
