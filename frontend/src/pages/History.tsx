import { useState } from "react";
import { LeadCard } from "../components/LeadCard";
import { useLeads } from "../hooks/useLeads";
import { formatDate } from "../utils/date";

const PAGE_SIZE = 10;

export function History() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useLeads(page, PAGE_SIZE);

  if (isLoading) {
    return (
      <div
        style={{
          padding: "2rem",
          color: "var(--ink-faint)",
          fontSize: "0.9rem",
          textAlign: "center",
        }}
      >
        Loading…
      </div>
    );
  }

  if (isError) {
    return (
      <div
        style={{
          padding: "2rem",
          color: "var(--ink-gray)",
          fontSize: "0.9rem",
          textAlign: "center",
        }}
      >
        Could not load history. Check your connection.
      </div>
    );
  }

  const leads = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

  if (leads.length === 0) {
    return (
      <div
        style={{
          padding: "3rem 1.5rem",
          color: "var(--ink-faint)",
          fontSize: "0.9rem",
          textAlign: "center",
        }}
      >
        No leads yet. Run the pipeline to generate some.
      </div>
    );
  }

  // Group by date, preserving insertion order
  const byDate = new Map<string, typeof leads>();
  for (const lead of leads) {
    const group = byDate.get(lead.date) ?? [];
    byDate.set(lead.date, [...group, lead]);
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "calc(100vh - 72px)",
      }}
    >
      {/* Lead groups */}
      <div style={{ flex: 1, padding: "1.5rem", overflowY: "auto" }}>
        {[...byDate.entries()].map(([date, dateLeads]) => (
          <section key={date} style={{ marginBottom: "2rem" }}>
            <h2
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "1rem",
                color: "var(--ink-gray)",
                fontWeight: 400,
                marginBottom: "0.75rem",
              }}
            >
              {formatDate(date)}
            </h2>
            <div style={{ display: "flex", gap: "1rem" }}>
              {dateLeads.map((lead) => (
                <LeadCard key={lead.id} lead={lead} date={date} />
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <footer
          style={{
            borderTop: "1px solid var(--paper-kraft)",
            padding: "1rem 1.5rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "1rem",
            backgroundColor: "var(--paper-white)",
            flexShrink: 0,
          }}
        >
          <button
            onClick={() => setPage((p) => p - 1)}
            disabled={page === 1}
            style={{
              fontSize: "0.82rem",
              padding: "5px 12px",
              border: "1px solid var(--paper-kraft)",
              borderRadius: "var(--radius-md)",
              backgroundColor: page === 1 ? "var(--paper-tan)" : "var(--paper-cream)",
              color: page === 1 ? "var(--ink-faint)" : "var(--ink-gray)",
              cursor: page === 1 ? "not-allowed" : "pointer",
            }}
          >
            ← previous
          </button>
          <span style={{ fontSize: "0.82rem", color: "var(--ink-light)" }}>
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page === totalPages}
            style={{
              fontSize: "0.82rem",
              padding: "5px 12px",
              border: "1px solid var(--paper-kraft)",
              borderRadius: "var(--radius-md)",
              backgroundColor:
                page === totalPages ? "var(--paper-tan)" : "var(--paper-cream)",
              color: page === totalPages ? "var(--ink-faint)" : "var(--ink-gray)",
              cursor: page === totalPages ? "not-allowed" : "pointer",
            }}
          >
            next →
          </button>
        </footer>
      )}
    </div>
  );
}
