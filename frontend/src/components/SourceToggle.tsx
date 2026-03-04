import { useSources, useToggleSource } from "../hooks/useInterests";
import type { ScraperSource } from "../types";
import { formatDate } from "../utils/date";

/**
 * List of scraper sources with enable/disable toggles and last-run status.
 */
export function SourceToggle() {
  const { data, isLoading, isError } = useSources();
  const toggleMutation = useToggleSource();

  if (isLoading) return <p style={{ color: "var(--ink-light)" }}>Loading sources…</p>;
  if (isError) return <p style={{ color: "var(--downvote)" }}>Failed to load sources.</p>;

  const sources = data?.items ?? [];

  if (sources.length === 0) {
    return <p style={{ color: "var(--ink-light)" }}>No scraper sources configured.</p>;
  }

  function handleToggle(source: ScraperSource) {
    toggleMutation.mutate({ id: source.id, enabled: !source.enabled });
  }

  return (
    <section>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {sources.map((source) => (
          <li
            key={source.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              padding: "0.75rem 0",
              borderBottom: "1px solid var(--paper-kraft)",
              opacity: source.enabled ? 1 : 0.5,
            }}
          >
            <input
              type="checkbox"
              checked={source.enabled}
              onChange={() => handleToggle(source)}
              disabled={toggleMutation.isPending}
              aria-label={`Toggle ${source.name}`}
            />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, color: "var(--ink-black)" }}>{source.name}</div>
              <div style={{ fontSize: "0.75rem", color: "var(--ink-light)" }}>
                {source.last_run_at
                  ? `Last run: ${formatDate(source.last_run_at.split("T")[0])} — ${statusLabel(source.last_run_status)}`
                  : "Never run"}
              </div>
            </div>
            <StatusBadge status={source.last_run_status} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function statusLabel(status: ScraperSource["last_run_status"]): string {
  if (status === "success") return "✓ success";
  if (status === "error") return "✗ error";
  if (status === "skipped") return "— skipped";
  return "";
}

function StatusBadge({ status }: { status: ScraperSource["last_run_status"] }) {
  if (!status) return null;
  const colors: Record<string, string> = {
    success: "var(--upvote)",
    error: "var(--downvote)",
    skipped: "#8c7c5c",
  };
  return (
    <span
      style={{
        fontSize: "0.7rem",
        background: colors[status] ?? "var(--ink-light)",
        color: "#fff",
        padding: "2px 6px",
        borderRadius: "var(--radius-sm)",
        fontWeight: 600,
      }}
    >
      {status}
    </span>
  );
}
