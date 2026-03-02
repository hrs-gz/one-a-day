/**
 * Format an ISO date string "YYYY-MM-DD" to a human-readable form.
 * e.g. "2025-03-01" → "March 1, 2025"
 */
export function formatDate(isoDate: string): string {
  // Parse as UTC to avoid timezone-shifting the date
  const [year, month, day] = isoDate.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}

/**
 * Return true if the given ISO date string represents today (in local time).
 */
export function isToday(isoDate: string): boolean {
  const today = new Date();
  const todayStr = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");
  return isoDate === todayStr;
}
