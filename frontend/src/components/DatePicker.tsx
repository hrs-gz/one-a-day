import { useCallback, useState } from "react";

interface DatePickerProps {
  value: string; // YYYY-MM-DD
  onSelect: (date: string) => void;
  onClose: () => void;
}

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

/**
 * Modal calendar date picker.
 * Pure implementation — no external library.
 */
export function DatePicker({ value, onSelect, onClose }: DatePickerProps) {
  const initial = value ? new Date(value + "T00:00:00") : new Date();
  const [viewYear, setViewYear] = useState(initial.getFullYear());
  const [viewMonth, setViewMonth] = useState(initial.getMonth()); // 0-indexed
  const [selected, setSelected] = useState(value);

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const prevMonth = useCallback(() => {
    setViewMonth((m) => {
      if (m === 0) { setViewYear((y) => y - 1); return 11; }
      return m - 1;
    });
  }, []);

  const nextMonth = useCallback(() => {
    setViewMonth((m) => {
      if (m === 11) { setViewYear((y) => y + 1); return 0; }
      return m + 1;
    });
  }, []);

  // Build day grid
  const firstDay = new Date(viewYear, viewMonth, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  // Pad to complete last row
  while (cells.length % 7 !== 0) cells.push(null);

  const toIso = (d: number) =>
    `${viewYear}-${String(viewMonth + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

  const isFuture = (d: number) => new Date(toIso(d) + "T00:00:00") > today;

  return (
    /* Overlay */
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(44,44,44,0.3)",
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Panel */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: "var(--paper-cream)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-picker)",
          padding: "1.5rem",
          width: "100%",
          maxWidth: 380,
        }}
      >
        {/* Month navigation */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "1rem",
          }}
        >
          <button
            onClick={prevMonth}
            style={{ fontSize: "1.1rem", color: "var(--ink-gray)", padding: "4px 8px" }}
          >
            ‹
          </button>
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "1.05rem",
              color: "var(--ink-black)",
            }}
          >
            {MONTHS[viewMonth]} {viewYear}
          </span>
          <button
            onClick={nextMonth}
            style={{ fontSize: "1.1rem", color: "var(--ink-gray)", padding: "4px 8px" }}
          >
            ›
          </button>
        </div>

        {/* Day headers */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", marginBottom: "0.5rem" }}>
          {DAYS.map((d) => (
            <div
              key={d}
              style={{
                textAlign: "center",
                fontSize: "0.7rem",
                color: "var(--ink-light)",
                fontWeight: 500,
                padding: "4px 0",
              }}
            >
              {d}
            </div>
          ))}
        </div>

        {/* Day grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "2px" }}>
          {cells.map((day, i) => {
            if (!day) return <div key={i} />;
            const iso = toIso(day);
            const isSelected = iso === selected;
            const isToday = iso === today.toISOString().slice(0, 10);
            const disabled = isFuture(day);
            return (
              <button
                key={i}
                onClick={() => !disabled && setSelected(iso)}
                disabled={disabled}
                style={{
                  textAlign: "center",
                  padding: "6px 0",
                  fontSize: "0.85rem",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: isSelected
                    ? "var(--accent)"
                    : isToday
                    ? "var(--paper-tan)"
                    : "transparent",
                  color: isSelected
                    ? "#fff"
                    : disabled
                    ? "var(--ink-faint)"
                    : "var(--ink-black)",
                  cursor: disabled ? "not-allowed" : "pointer",
                  fontWeight: isToday ? 600 : 400,
                }}
              >
                {day}
              </button>
            );
          })}
        </div>

        {/* Actions */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: "0.75rem",
            marginTop: "1.25rem",
          }}
        >
          <button
            onClick={onClose}
            style={{
              padding: "6px 16px",
              fontSize: "0.85rem",
              color: "var(--ink-gray)",
              border: "1px solid var(--paper-kraft)",
              borderRadius: "var(--radius-md)",
              backgroundColor: "transparent",
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => { onSelect(selected); onClose(); }}
            style={{
              padding: "6px 16px",
              fontSize: "0.85rem",
              color: "#fff",
              backgroundColor: "var(--accent)",
              borderRadius: "var(--radius-md)",
              border: "none",
            }}
          >
            OK
          </button>
        </div>
      </div>
    </div>
  );
}
