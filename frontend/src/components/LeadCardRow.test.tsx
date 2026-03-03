import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Lead } from "../types";
import { LeadCardRow } from "./LeadCardRow";

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const baseLead: Lead = {
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

describe("LeadCardRow", () => {
  it("shows no lead names and no empty slots while loading", () => {
    render(<LeadCardRow leads={[]} isLoading={true} date="2025-03-01" />, {
      wrapper: Wrapper,
    });
    expect(screen.queryByText("Dr. Jane Smith")).not.toBeInTheDocument();
    expect(screen.queryByText("—")).not.toBeInTheDocument();
  });

  it("shows 3 empty slots when leads array is empty", () => {
    render(<LeadCardRow leads={[]} isLoading={false} date="2025-03-01" />, {
      wrapper: Wrapper,
    });
    expect(screen.getAllByText("—")).toHaveLength(3);
  });

  it("pads with empty slots when fewer than 3 leads", () => {
    render(
      <LeadCardRow leads={[baseLead]} isLoading={false} date="2025-03-01" />,
      { wrapper: Wrapper }
    );
    expect(screen.getByText("Dr. Jane Smith")).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
  });

  it("renders all 3 leads with no empty slots", () => {
    const leads: Lead[] = [
      baseLead,
      { ...baseLead, id: 2, rank: 2, name: "Alice Nguyen" },
      { ...baseLead, id: 3, rank: 3, name: "Bob Chen" },
    ];
    render(
      <LeadCardRow leads={leads} isLoading={false} date="2025-03-01" />,
      { wrapper: Wrapper }
    );
    expect(screen.getByText("Dr. Jane Smith")).toBeInTheDocument();
    expect(screen.getByText("Alice Nguyen")).toBeInTheDocument();
    expect(screen.getByText("Bob Chen")).toBeInTheDocument();
    expect(screen.queryByText("—")).not.toBeInTheDocument();
  });
});
