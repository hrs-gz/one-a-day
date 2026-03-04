import type { Lead } from "../types";
import { LeadCard } from "./LeadCard";

interface LeadCardRowProps {
  leads: Lead[];
  isLoading: boolean;
  date: string;
}

/**
 * Renders a horizontal row of up to 3 lead cards.
 * Shows skeleton placeholders while loading.
 * Shows empty-state slots if leads.length < 3.
 */
export function LeadCardRow({ leads, isLoading, date }: LeadCardRowProps) {
  if (isLoading) {
    return (
      <div style={rowStyle}>
        {[1, 2, 3].map((i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (leads.length === 0) {
    return (
      <div style={rowStyle}>
        {[1, 2, 3].map((i) => (
          <EmptyCard key={i} />
        ))}
      </div>
    );
  }

  // Pad with empty slots if fewer than 3
  const slots = [...leads];
  while (slots.length < 3) {
    // placeholder marker — won't render as LeadCard
    slots.push(null as unknown as Lead);
  }

  return (
    <div style={rowStyle}>
      {slots.map((lead, i) =>
        lead ? (
          <LeadCard key={lead.id} lead={lead} date={date} />
        ) : (
          <EmptyCard key={`empty-${i}`} />
        )
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const rowStyle: React.CSSProperties = {
  display: "flex",
  gap: "1rem",
  alignItems: "stretch",
  justifyContent: "center",
  padding: "0 1rem",
};

function SkeletonCard() {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        maxWidth: 360,
        backgroundColor: "var(--paper-cream)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-card)",
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
      }}
    >
      <div style={skeletonLine("30%", "0.75rem")} />
      <div style={skeletonLine("70%", "1rem")} />
      <div style={skeletonLine("55%", "0.75rem")} />
      <div style={{ flex: 1 }} />
      <div style={skeletonLine("40%", "0.6rem")} />
    </div>
  );
}

function EmptyCard() {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        maxWidth: 360,
        backgroundColor: "var(--paper-cream)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-card)",
        padding: "1.25rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 200,
        color: "var(--ink-faint)",
        fontSize: "0.8rem",
      }}
    >
      —
    </div>
  );
}

function skeletonLine(width: string, height: string): React.CSSProperties {
  return {
    width,
    height,
    backgroundColor: "var(--paper-tan)",
    borderRadius: "var(--radius-sm)",
    animation: "pulse 1.5s ease-in-out infinite",
  };
}
