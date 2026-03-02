import { useState } from "react";
import { useDeleteInterest, useUpdateInterest } from "../hooks/useInterests";
import type { InterestConfig } from "../types";

interface TagCloudProps {
  interests: InterestConfig[];
}

/**
 * Flex-wrap tag cloud where font size is proportional to interest weight.
 * Click a tag → inline editor with weight slider + delete button.
 */
export function TagCloud({ interests }: TagCloudProps) {
  const [editingId, setEditingId] = useState<number | null>(null);

  if (interests.length === 0) {
    return (
      <div
        style={{
          color: "var(--ink-faint)",
          fontSize: "0.9rem",
          textAlign: "center",
          padding: "3rem 1rem",
        }}
      >
        No interests yet. Add some below.
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "0.75rem",
        padding: "1.5rem",
        justifyContent: "center",
        alignContent: "center",
        flex: 1,
      }}
    >
      {interests.map((interest) =>
        editingId === interest.id ? (
          <TagEditor
            key={interest.id}
            interest={interest}
            onDone={() => setEditingId(null)}
          />
        ) : (
          <TagChip
            key={interest.id}
            interest={interest}
            onClick={() => setEditingId(interest.id)}
          />
        )
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface TagChipProps {
  interest: InterestConfig;
  onClick: () => void;
}

function TagChip({ interest, onClick }: TagChipProps) {
  // Map weight 0.0–1.0 → font size 0.8rem–2.2rem
  const fontSize = 0.8 + interest.weight * 1.4;

  return (
    <button
      onClick={onClick}
      style={{
        fontSize: `${fontSize}rem`,
        color: interest.active ? "var(--accent)" : "var(--ink-faint)",
        background: "transparent",
        border: "none",
        cursor: "pointer",
        fontFamily: "var(--font-display)",
        transition: "color 0.15s ease",
        lineHeight: 1.3,
        padding: "2px 4px",
      }}
    >
      {interest.keyword}
    </button>
  );
}

interface TagEditorProps {
  interest: InterestConfig;
  onDone: () => void;
}

function TagEditor({ interest, onDone }: TagEditorProps) {
  const [weight, setWeight] = useState(interest.weight);
  const updateMutation = useUpdateInterest();
  const deleteMutation = useDeleteInterest();

  const handleSave = () => {
    updateMutation.mutate({ id: interest.id, payload: { weight } }, { onSuccess: onDone });
  };

  const handleDelete = () => {
    deleteMutation.mutate(interest.id, { onSuccess: onDone });
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.4rem",
        backgroundColor: "var(--paper-tan)",
        borderRadius: "var(--radius-md)",
        padding: "0.75rem",
        minWidth: 160,
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1rem",
          color: "var(--ink-black)",
        }}
      >
        {interest.keyword}
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={weight}
          onChange={(e) => setWeight(parseFloat(e.target.value))}
          style={{ flex: 1, accentColor: "var(--accent)" }}
        />
        <span style={{ fontSize: "0.75rem", color: "var(--ink-gray)", minWidth: 28 }}>
          {weight.toFixed(2)}
        </span>
      </div>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          onClick={handleSave}
          style={{
            flex: 1,
            fontSize: "0.75rem",
            padding: "3px 8px",
            backgroundColor: "var(--accent)",
            color: "#fff",
            borderRadius: "var(--radius-sm)",
            border: "none",
          }}
        >
          Save
        </button>
        <button
          onClick={handleDelete}
          style={{
            fontSize: "0.75rem",
            padding: "3px 8px",
            color: "var(--downvote)",
            border: "1px solid var(--downvote)",
            borderRadius: "var(--radius-sm)",
            background: "transparent",
          }}
        >
          Delete
        </button>
        <button
          onClick={onDone}
          style={{
            fontSize: "0.75rem",
            padding: "3px 8px",
            color: "var(--ink-light)",
            border: "1px solid var(--paper-kraft)",
            borderRadius: "var(--radius-sm)",
            background: "transparent",
          }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
