import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { DatePicker } from "../components/DatePicker";
import { LeadCardRow } from "../components/LeadCardRow";
import { useLeadsByDate } from "../hooks/useLeads";
import { formatDate } from "../utils/date";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Dashboard page — 3 lead cards for the selected date + date navigation + write button.
 *
 * Layout:
 *   Body: LeadCardRow (3 cards)
 *   Footer: date chip (→ DatePicker modal) + write button (→ /algorithm)
 */
export function Dashboard() {
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState(todayIso);
  const [pickerOpen, setPickerOpen] = useState(false);

  const { data: leads = [], isLoading } = useLeadsByDate(selectedDate);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 72px)", // subtract header height
      }}
    >
      {/* Card row — takes remaining space */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
          padding: "1.5rem 0",
        }}
      >
        <LeadCardRow leads={leads} isLoading={isLoading} date={selectedDate} />
      </div>

      {/* Footer */}
      <footer
        style={{
          borderTop: "1px solid var(--paper-kraft)",
          padding: "1rem 1.5rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          backgroundColor: "var(--paper-white)",
          flexShrink: 0,
        }}
      >
        {/* Date chip — opens picker */}
        <button
          onClick={() => setPickerOpen(true)}
          style={{
            fontSize: "0.85rem",
            color: "var(--ink-gray)",
            background: "var(--paper-cream)",
            border: "1px solid var(--paper-kraft)",
            borderRadius: "var(--radius-md)",
            padding: "6px 14px",
            cursor: "pointer",
            fontFamily: "var(--font-body)",
          }}
        >
          {selectedDate === todayIso()
            ? "today"
            : formatDate(selectedDate)}
        </button>

        {/* Write / edit button → Algorithm */}
        <button
          onClick={() => navigate("/algorithm")}
          aria-label="Open algorithm editor"
          style={{
            width: 40,
            height: 40,
            borderRadius: "50%",
            backgroundColor: "var(--accent)",
            color: "#fff",
            fontSize: "1.2rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "none",
            cursor: "pointer",
            boxShadow: "var(--shadow-hover)",
          }}
        >
          ✏
        </button>
      </footer>

      {/* Date picker modal */}
      {pickerOpen && (
        <DatePicker
          value={selectedDate}
          onSelect={setSelectedDate}
          onClose={() => setPickerOpen(false)}
        />
      )}
    </div>
  );
}
