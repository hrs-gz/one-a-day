import { useCallback, useRef } from "react";
import type { Lead } from "../types";
import { useFavoriteLead, useVoteLead } from "../hooks/useLeads";

interface LeadCardProps {
  lead: Lead;
  date: string;
}

/**
 * Lead card per design spec:
 * - ☆/★ favorite toggle (top-left)
 * - Name (Instrument Serif)
 * - title · affiliation (ink-gray)
 * - contact | source links
 * - 👍 ☀ 👎 vote row (debounced 300ms)
 */
export function LeadCard({ lead, date }: LeadCardProps) {
  const voteMutation = useVoteLead(date);
  const favoriteMutation = useFavoriteLead(date);
  const voteTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleVote = useCallback(
    (v: -1 | 0 | 1) => {
      if (voteTimer.current) clearTimeout(voteTimer.current);
      voteTimer.current = setTimeout(() => {
        const next = lead.vote === v ? 0 : v;
        voteMutation.mutate({ id: lead.id, vote: next });
      }, 300);
    },
    [lead.id, lead.vote, voteMutation]
  );

  const handleFavorite = useCallback(() => {
    favoriteMutation.mutate({ id: lead.id, favorited: !lead.favorited });
  }, [lead.id, lead.favorited, favoriteMutation]);

  const contactHref = lead.contact_hint
    ? lead.contact_hint.startsWith("http")
      ? lead.contact_hint
      : `mailto:${lead.contact_hint}`
    : null;

  return (
    <article
      style={{
        backgroundColor: "var(--paper-cream)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-card)",
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.6rem",
        position: "relative",
        transition: "box-shadow 0.15s ease",
        flex: "1 1 300px",
        maxWidth: "400px",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-hover)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-card)";
      }}
    >
      {/* Favorite toggle */}
      <button
        onClick={handleFavorite}
        aria-label={lead.favorited ? "Remove from favorites" : "Add to favorites"}
        style={{
          position: "absolute",
          top: "1rem",
          left: "1rem",
          fontSize: "1.1rem",
          color: lead.favorited ? "#e6a817" : "var(--ink-faint)",
          transition: "color 0.15s ease",
          padding: "2px",
          lineHeight: 1,
        }}
      >
        {lead.favorited ? "★" : "☆"}
      </button>

      {/* Name */}
      <h2
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.15rem",
          fontWeight: 400,
          color: "var(--ink-black)",
          lineHeight: 1.3,
          marginTop: "1.5rem",
          paddingRight: "0.5rem",
        }}
      >
        {lead.name}
      </h2>

      {/* Title · Affiliation */}
      <p
        style={{
          fontSize: "0.85rem",
          color: "var(--ink-gray)",
          lineHeight: 1.4,
        }}
      >
        {lead.title}
        {lead.affiliation && (
          <span style={{ color: "var(--ink-light)" }}> · {lead.affiliation}</span>
        )}
      </p>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Contact | Source row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          fontSize: "0.78rem",
          flexWrap: "wrap",
        }}
      >
        {contactHref && (
          <>
            <a
              href={contactHref}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--accent)", textDecoration: "none" }}
            >
              contact
            </a>
            <span style={{ color: "var(--ink-faint)" }}>|</span>
          </>
        )}
        <a
          href={lead.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: "var(--ink-light)",
            textDecoration: "none",
            fontSize: "0.72rem",
            background: "var(--paper-tan)",
            padding: "1px 6px",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {lead.source_type}
        </a>
      </div>

      {/* Vote row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "1.5rem",
          paddingTop: "0.5rem",
          borderTop: "1px solid var(--paper-kraft)",
        }}
      >
        <VoteButton
          emoji="👍"
          active={lead.vote === 1}
          activeColor="var(--upvote)"
          onClick={() => handleVote(1)}
          label="Upvote"
        />
        <VoteButton
          emoji="☀"
          active={lead.vote === 0}
          activeColor="var(--ink-gray)"
          onClick={() => handleVote(0)}
          label="Neutral"
        />
        <VoteButton
          emoji="👎"
          active={lead.vote === -1}
          activeColor="var(--downvote)"
          onClick={() => handleVote(-1)}
          label="Downvote"
        />
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Sub-component
// ---------------------------------------------------------------------------

interface VoteButtonProps {
  emoji: string;
  active: boolean;
  activeColor: string;
  onClick: () => void;
  label: string;
}

function VoteButton({ emoji, active, activeColor, onClick, label }: VoteButtonProps) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      style={{
        fontSize: "1.1rem",
        opacity: active ? 1 : 0.35,
        filter: active ? "none" : "grayscale(1)",
        transition: "opacity 0.15s ease, filter 0.15s ease",
        color: active ? activeColor : "inherit",
        padding: "4px 6px",
        borderRadius: "var(--radius-sm)",
      }}
    >
      {emoji}
    </button>
  );
}
