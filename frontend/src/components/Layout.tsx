import { Outlet } from "react-router-dom";

/**
 * Top-level layout — "today is the day" header + main content area.
 * Footer is rendered by each page via the <Outlet />.
 */
export function Layout() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        backgroundColor: "var(--paper-white)",
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          padding: "1.25rem 1.5rem",
          borderBottom: "1px solid var(--paper-kraft)",
          backgroundColor: "var(--paper-white)",
        }}
      >
        {/* Hamburger — deferred, no action */}
        <button
          aria-label="Menu"
          style={{
            position: "absolute",
            left: "1.5rem",
            fontSize: "1.2rem",
            color: "var(--ink-light)",
            lineHeight: 1,
            padding: "4px",
          }}
        >
          ☰
        </button>

        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.5rem",
            fontWeight: 400,
            color: "var(--ink-black)",
            letterSpacing: "-0.01em",
          }}
        >
          today is the day
        </h1>
      </header>

      {/* Page content */}
      <main style={{ flex: 1 }}>
        <Outlet />
      </main>
    </div>
  );
}
