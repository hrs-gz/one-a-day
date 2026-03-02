import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { parseInterests } from "../api/interests";
import { interestKeys } from "../hooks/useInterests";

/**
 * Natural language interest input.
 * Textarea + icon toolbar + submit button.
 * On submit: calls /interests/parse → invalidates interest query.
 */
export function AlgorithmInput() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async () => {
    const trimmed = text.trim();
    if (!trimmed) return;

    setLoading(true);
    setFeedback(null);

    try {
      const result = await parseInterests({ text: trimmed });
      const created = result.created.length;
      const skipped = result.skipped.length;
      setFeedback(
        created > 0
          ? `Added ${created} keyword${created > 1 ? "s" : ""}${skipped > 0 ? `, skipped ${skipped} duplicate${skipped > 1 ? "s" : ""}` : ""}.`
          : `No new keywords (${skipped} already existed).`
      );
      setText("");
      queryClient.invalidateQueries({ queryKey: interestKeys.all });
    } catch {
      setFeedback("Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleSubmit();
    }
  };

  return (
    <div
      style={{
        backgroundColor: "var(--paper-cream)",
        border: "1px solid var(--paper-kraft)",
        borderRadius: "var(--radius-lg)",
        padding: "0.75rem 1rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
      }}
    >
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="What would you like to know?"
        rows={3}
        style={{
          resize: "none",
          border: "none",
          background: "transparent",
          fontSize: "0.9rem",
          color: "var(--ink-black)",
          fontFamily: "var(--font-body)",
          outline: "none",
          lineHeight: 1.5,
          width: "100%",
        }}
      />

      {/* Toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {/* Icon row — display only in v1 */}
        <div
          style={{
            display: "flex",
            gap: "1rem",
            fontSize: "1rem",
            color: "var(--ink-faint)",
          }}
        >
          <span title="Attach image">🖼</span>
          <span title="Code snippet">&lt;/&gt;</span>
          <span title="Voice input">🎤</span>
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={loading || !text.trim()}
          aria-label="Submit"
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            backgroundColor:
              loading || !text.trim() ? "var(--paper-kraft)" : "var(--accent)",
            color: loading || !text.trim() ? "var(--ink-faint)" : "#fff",
            fontSize: "1rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "background-color 0.15s ease",
            border: "none",
            cursor: loading || !text.trim() ? "not-allowed" : "pointer",
          }}
        >
          ↑
        </button>
      </div>

      {/* Feedback */}
      {feedback && (
        <p style={{ fontSize: "0.78rem", color: "var(--ink-gray)", margin: 0 }}>
          {feedback}
        </p>
      )}
    </div>
  );
}
