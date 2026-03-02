import { useState } from "react";
import { useCreateSource } from "../hooks/useInterests";

const SCRAPER_OPTIONS = [
  { label: "University Faculty", value: "app.scrapers.university.UniversityScraper" },
  { label: "Company Team Page", value: "app.scrapers.company.CompanyScraper" },
  { label: "News", value: "app.scrapers.news.NewsScraper" },
  { label: "Local News", value: "app.scrapers.local_news.LocalNewsScraper" },
  { label: "Personal Site", value: "app.scrapers.personal_site.PersonalSiteScraper" },
  { label: "RSS Feed", value: "app.scrapers.rss.RssScraper" },
  { label: "Substack", value: "app.scrapers.substack.SubstackScraper" },
];

interface AddSourceFormProps {
  onDone: () => void;
}

export function AddSourceForm({ onDone }: AddSourceFormProps) {
  const [name, setName] = useState("");
  const [scraperClass, setScraperClass] = useState(SCRAPER_OPTIONS[0].value);
  const [urls, setUrls] = useState("");
  const createMutation = useCreateSource();

  const handleSubmit = () => {
    const trimmedName = name.trim();
    const seedUrls = urls
      .split("\n")
      .map((u) => u.trim())
      .filter(Boolean);

    if (!trimmedName || seedUrls.length === 0) return;

    const config = JSON.stringify({ seed_urls: seedUrls });

    createMutation.mutate(
      { name: trimmedName, scraper_class: scraperClass, config },
      {
        onSuccess: () => {
          setName("");
          setUrls("");
          onDone();
        },
      }
    );
  };

  return (
    <div
      style={{
        backgroundColor: "var(--paper-cream)",
        border: "1px solid var(--paper-kraft)",
        borderRadius: "var(--radius-lg)",
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
      }}
    >
      <h3
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1rem",
          fontWeight: 400,
          color: "var(--ink-black)",
          margin: 0,
        }}
      >
        Add Source
      </h3>

      {/* Name */}
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Source name (e.g. MIT Faculty Directory)"
        style={inputStyle}
      />

      {/* Scraper type */}
      <select
        value={scraperClass}
        onChange={(e) => setScraperClass(e.target.value)}
        style={inputStyle}
      >
        {SCRAPER_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Seed URLs */}
      <textarea
        value={urls}
        onChange={(e) => setUrls(e.target.value)}
        placeholder="Seed URLs (one per line)"
        rows={4}
        style={{
          ...inputStyle,
          resize: "vertical",
          lineHeight: 1.5,
        }}
      />

      {/* Actions */}
      <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
        <button
          onClick={onDone}
          style={{
            fontSize: "0.82rem",
            color: "var(--ink-light)",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            padding: "6px 12px",
          }}
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={createMutation.isPending || !name.trim() || !urls.trim()}
          style={{
            fontSize: "0.82rem",
            color: "#fff",
            backgroundColor:
              createMutation.isPending || !name.trim() || !urls.trim()
                ? "var(--paper-kraft)"
                : "var(--accent)",
            border: "none",
            borderRadius: "var(--radius-md)",
            padding: "6px 16px",
            cursor:
              createMutation.isPending || !name.trim() || !urls.trim()
                ? "not-allowed"
                : "pointer",
            transition: "background-color 0.15s ease",
          }}
        >
          {createMutation.isPending ? "Adding…" : "Add"}
        </button>
      </div>

      {createMutation.isError && (
        <p style={{ fontSize: "0.78rem", color: "var(--downvote)", margin: 0 }}>
          Failed to create source. Try again.
        </p>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  fontFamily: "var(--font-body)",
  fontSize: "0.85rem",
  color: "var(--ink-black)",
  backgroundColor: "var(--paper-white)",
  border: "1px solid var(--paper-kraft)",
  borderRadius: "var(--radius-md)",
  padding: "8px 10px",
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};
