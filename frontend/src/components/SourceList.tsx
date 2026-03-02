import { useState } from "react";
import {
  useDeleteSource,
  useSources,
  useToggleSource,
} from "../hooks/useInterests";
import type { ScraperSource } from "../types";
import { formatDate } from "../utils/date";
import { AddSourceForm } from "./AddSourceForm";

export function SourceList() {
  const { data, isLoading, isError } = useSources();
  const toggleMutation = useToggleSource();
  const deleteMutation = useDeleteSource();
  const [showAdd, setShowAdd] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  if (isLoading) {
    return (
      <p style={{ color: "var(--ink-faint)", fontSize: "0.9rem" }}>
        Loading sources…
      </p>
    );
  }

  if (isError) {
    return (
      <p style={{ color: "var(--downvote)", fontSize: "0.9rem" }}>
        Failed to load sources.
      </p>
    );
  }

  const sources = data?.items ?? [];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
        maxWidth: 600,
        margin: "0 auto",
        width: "100%",
      }}
    >
      <h2
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.25rem",
          fontWeight: 400,
          color: "var(--ink-black)",
          margin: 0,
        }}
      >
        Sources
      </h2>

      {sources.length === 0 && !showAdd && (
        <p style={{ color: "var(--ink-faint)", fontSize: "0.85rem" }}>
          No sources configured yet.
        </p>
      )}

      {sources.map((source) => (
        <SourceRow
          key={source.id}
          source={source}
          onToggle={() =>
            toggleMutation.mutate({ id: source.id, enabled: !source.enabled })
          }
          togglePending={toggleMutation.isPending}
          onDelete={() => {
            if (confirmDeleteId === source.id) {
              deleteMutation.mutate(source.id, {
                onSuccess: () => setConfirmDeleteId(null),
              });
            } else {
              setConfirmDeleteId(source.id);
            }
          }}
          confirmingDelete={confirmDeleteId === source.id}
          onCancelDelete={() => setConfirmDeleteId(null)}
        />
      ))}

      {showAdd ? (
        <AddSourceForm onDone={() => setShowAdd(false)} />
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          style={{
            alignSelf: "flex-start",
            fontSize: "0.85rem",
            color: "var(--accent)",
            background: "transparent",
            border: "1px dashed var(--paper-kraft)",
            borderRadius: "var(--radius-md)",
            padding: "8px 16px",
            cursor: "pointer",
            marginTop: "0.25rem",
          }}
        >
          + Add source
        </button>
      )}
    </div>
  );
}

function SourceRow({
  source,
  onToggle,
  togglePending,
  onDelete,
  confirmingDelete,
  onCancelDelete,
}: {
  source: ScraperSource;
  onToggle: () => void;
  togglePending: boolean;
  onDelete: () => void;
  confirmingDelete: boolean;
  onCancelDelete: () => void;
}) {
  const scraperLabel =
    source.scraper_class.split(".").pop()?.replace("Scraper", "") ?? "";

  return (
    <div
      style={{
        backgroundColor: "var(--paper-cream)",
        borderRadius: "var(--radius-lg)",
        padding: "1rem 1.25rem",
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        opacity: source.enabled ? 1 : 0.5,
        transition: "opacity 0.15s ease",
      }}
    >
      {/* Enable toggle */}
      <input
        type="checkbox"
        checked={source.enabled}
        onChange={onToggle}
        disabled={togglePending}
        title="Enable/disable"
        style={{ accentColor: "var(--accent)", cursor: "pointer" }}
      />

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "0.95rem",
            color: "var(--ink-black)",
            lineHeight: 1.3,
          }}
        >
          {source.name}
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginTop: "0.25rem",
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontSize: "0.7rem",
              background: "var(--paper-tan)",
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              color: "var(--ink-light)",
            }}
          >
            {scraperLabel}
          </span>
          <span style={{ fontSize: "0.72rem", color: "var(--ink-faint)" }}>
            {source.last_run_at
              ? `${formatDate(source.last_run_at.split("T")[0])} — ${statusText(source.last_run_status)}`
              : "Never run"}
          </span>
        </div>
      </div>

      {/* Status badge */}
      {source.last_run_status && (
        <StatusBadge status={source.last_run_status} />
      )}

      {/* Delete */}
      {confirmingDelete ? (
        <div style={{ display: "flex", gap: "0.25rem" }}>
          <button
            onClick={onDelete}
            style={{
              fontSize: "0.72rem",
              color: "#fff",
              backgroundColor: "var(--downvote)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              padding: "3px 8px",
              cursor: "pointer",
            }}
          >
            Confirm
          </button>
          <button
            onClick={onCancelDelete}
            style={{
              fontSize: "0.72rem",
              color: "var(--ink-light)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              padding: "3px 4px",
            }}
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={onDelete}
          title="Delete source"
          style={{
            fontSize: "0.9rem",
            color: "var(--ink-faint)",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            padding: "2px 4px",
            lineHeight: 1,
          }}
        >
          ×
        </button>
      )}
    </div>
  );
}

function statusText(status: ScraperSource["last_run_status"]): string {
  if (status === "success") return "success";
  if (status === "error") return "error";
  if (status === "skipped") return "skipped";
  return "";
}

function StatusBadge({
  status,
}: {
  status: NonNullable<ScraperSource["last_run_status"]>;
}) {
  const colors: Record<string, string> = {
    success: "#059669",
    error: "#dc2626",
    skipped: "#d97706",
  };
  return (
    <span
      style={{
        fontSize: "0.65rem",
        background: colors[status] ?? "var(--ink-faint)",
        color: "#fff",
        padding: "2px 6px",
        borderRadius: "var(--radius-sm)",
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.03em",
      }}
    >
      {status}
    </span>
  );
}
