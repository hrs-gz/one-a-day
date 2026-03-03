import { SourceToggle } from "../components/SourceToggle";

export function Settings() {
  return (
    <div
      style={{
        padding: "1.5rem",
        maxWidth: 700,
        margin: "0 auto",
      }}
    >
      <h2
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.3rem",
          fontWeight: 400,
          color: "var(--ink-black)",
          marginBottom: "1.5rem",
        }}
      >
        Sources
      </h2>
      <SourceToggle />
    </div>
  );
}
