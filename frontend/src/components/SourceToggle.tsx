import { useSources, useToggleSource } from "../hooks/useInterests";
import type { ScraperSource } from "../types";
import { formatDate } from "../utils/date";

/**
 * List of scraper sources with enable/disable toggles and last-run status.
 */
export function SourceToggle() {
  const { data, isLoading, isError } = useSources();
  const toggleMutation = useToggleSource();

  if (isLoading) return <p>Loading sources…</p>;
  if (isError) return <p style={{ color: "red" }}>Failed to load sources.</p>;

  const sources = data?.items ?? [];

  if (sources.length === 0) {
    return <p style={{ color: "#6b7280" }}>No scraper sources configured.</p>;
  }

  function handleToggle(source: ScraperSource) {
    toggleMutation.mutate({ id: source.id, enabled: !source.enabled });
  }

  return (
    <section>
      <h3 style={{ marginBottom: "1rem" }}>Scraper Sources</h3>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {sources.map((source) => (
          <li
            key={source.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              padding: "0.75rem 0",
              borderBottom: "1px solid #f3f4f6",
              opacity: source.enabled ? 1 : 0.5,
            }}
          >
            <input
              type="checkbox"
              checked={source.enabled}
              onChange={() => handleToggle(source)}
              disabled={toggleMutation.isPending}
              title="Enable/disable this source"
            />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500 }}>{source.name}</div>
              <div style={{ fontSize: "0.75rem", color: "#6b7280" }}>
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
    success: "#059669",
    error: "#dc2626",
    skipped: "#d97706",
  };
  return (
    <span
      style={{
        fontSize: "0.7rem",
        background: colors[status] ?? "#6b7280",
        color: "#fff",
        padding: "2px 6px",
        borderRadius: 4,
        fontWeight: 600,
      }}
    >
      {status}
    </span>
  );
}
