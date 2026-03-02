import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

/**
 * Top-level layout — "today is the day" header + main content area.
 * Footer is rendered by each page via the <Outlet />.
 */
export function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);

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
        <button
          aria-label="Menu"
          onClick={() => setMenuOpen(!menuOpen)}
          style={{
            position: "absolute",
            left: "1.5rem",
            fontSize: "1.2rem",
            color: "var(--ink-light)",
            lineHeight: 1,
            padding: "4px",
            cursor: "pointer",
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

      {/* Slide-out menu */}
      {menuOpen && (
        <>
          <div
            onClick={() => setMenuOpen(false)}
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 90,
              backgroundColor: "rgba(44, 44, 44, 0.15)",
            }}
          />
          <nav
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              bottom: 0,
              width: 260,
              zIndex: 100,
              backgroundColor: "var(--paper-white)",
              borderRight: "1px solid var(--paper-kraft)",
              padding: "5rem 1.5rem 2rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.25rem",
              boxShadow: "var(--shadow-picker)",
            }}
          >
            <MenuLink to="/" onClick={() => setMenuOpen(false)}>
              Dashboard
            </MenuLink>
            <MenuLink to="/algorithm" onClick={() => setMenuOpen(false)}>
              Algorithm
            </MenuLink>
            <MenuLink to="/sources" onClick={() => setMenuOpen(false)}>
              Sources
            </MenuLink>
          </nav>
        </>
      )}

      {/* Page content */}
      <main style={{ flex: 1 }}>
        <Outlet />
      </main>
    </div>
  );
}

function MenuLink({
  to,
  onClick,
  children,
}: {
  to: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      style={({ isActive }) => ({
        fontFamily: "var(--font-display)",
        fontSize: "1.1rem",
        color: isActive ? "var(--accent)" : "var(--ink-gray)",
        textDecoration: "none",
        padding: "0.6rem 0.75rem",
        borderRadius: "var(--radius-md)",
        backgroundColor: isActive ? "var(--paper-cream)" : "transparent",
        transition: "background-color 0.15s ease",
      })}
    >
      {children}
    </NavLink>
  );
}
