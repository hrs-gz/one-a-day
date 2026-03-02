import { useNavigate } from "react-router-dom";
import { SourceList } from "../components/SourceList";

/**
 * Sources page — manage scraper sources (view, add, toggle, delete).
 *
 * Layout:
 *   Body: SourceList (flex: 1, scrollable)
 *   Footer: back button
 */
export function Sources() {
  const navigate = useNavigate();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 72px)",
      }}
    >
      {/* Source list */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: "1.5rem 2rem",
        }}
      >
        <SourceList />
      </div>

      {/* Footer */}
      <footer
        style={{
          borderTop: "1px solid var(--paper-kraft)",
          padding: "1rem 1.5rem",
          backgroundColor: "var(--paper-white)",
          flexShrink: 0,
        }}
      >
        <button
          onClick={() => navigate("/")}
          style={{
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
