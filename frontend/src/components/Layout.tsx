import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";

const NAV_ITEMS = [
  { label: "Dashboard", path: "/" },
  { label: "History", path: "/history" },
  { label: "Sources", path: "/settings" },
] as const;

export function Layout() {
  const navigate = useNavigate();
  const [navOpen, setNavOpen] = useState(false);

  const go = (path: string) => {
    navigate(path);
    setNavOpen(false);
  };

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
          zIndex: 20,
        }}
      >
        {/* Hamburger */}
        <button
          aria-label="Menu"
          aria-expanded={navOpen}
          onClick={() => setNavOpen((o) => !o)}
          style={{
            position: "absolute",
            left: "1.5rem",
            fontSize: "1.2rem",
            color: "var(--ink-light)",
            lineHeight: 1,
            padding: "4px",
            background: "transparent",
            border: "none",
            cursor: "pointer",
          }}
        >
          ☰
        </button>

        {/* Nav dropdown */}
        {navOpen && (
          <>
            {/* Click-outside overlay */}
            <div
              aria-hidden="true"
              onClick={() => setNavOpen(false)}
              style={{ position: "fixed", inset: 0, zIndex: 9 }}
            />
            <nav
              aria-label="Main navigation"
              style={{
                position: "absolute",
                top: "calc(100% + 4px)",
                left: "1.5rem",
                zIndex: 10,
                backgroundColor: "var(--paper-cream)",
                border: "1px solid var(--paper-kraft)",
                borderRadius: "var(--radius-md)",
                boxShadow: "var(--shadow-picker)",
                padding: "0.35rem 0",
                minWidth: 160,
              }}
            >
              {NAV_ITEMS.map(({ label, path }) => (
                <button
                  key={path}
                  onClick={() => go(path)}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    padding: "0.55rem 1rem",
                    fontSize: "0.9rem",
                    color: "var(--ink-black)",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    fontFamily: "var(--font-body)",
                  }}
                >
                  {label}
                </button>
              ))}
            </nav>
          </>
        )}

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
