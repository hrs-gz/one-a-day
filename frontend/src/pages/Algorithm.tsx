import { useNavigate } from "react-router-dom";
import { AlgorithmInput } from "../components/AlgorithmInput";
import { TagCloud } from "../components/TagCloud";
import { useInterests } from "../hooks/useInterests";

/**
 * Algorithm page — wordcloud of interest tags + NL input.
 *
 * Layout:
 *   Body: TagCloud (flex: 1, scrollable)
 *   Footer: AlgorithmInput + back button
 */
export function Algorithm() {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useInterests();
  const interests = data?.items ?? [];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 72px)",
      }}
    >
      {/* Tag cloud */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {isLoading ? (
          <p style={{ color: "var(--ink-faint)", fontSize: "0.9rem" }}>Loading…</p>
        ) : isError ? (
          <p style={{ color: "var(--ink-gray)", fontSize: "0.9rem" }}>
            Could not load interests. Check your connection.
          </p>
        ) : (
          <TagCloud interests={interests} />
        )}
      </div>

      {/* Footer */}
      <footer
        style={{
          borderTop: "1px solid var(--paper-kraft)",
          padding: "1rem 1.5rem",
          backgroundColor: "var(--paper-white)",
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
          flexShrink: 0,
        }}
      >
        <AlgorithmInput />

        {/* Back button */}
        <button
          onClick={() => navigate("/")}
          style={{
            alignSelf: "flex-start",
            fontSize: "0.82rem",
            color: "var(--ink-light)",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.25rem",
            padding: 0,
          }}
        >
          ← back
        </button>
      </footer>
    </div>
  );
}
