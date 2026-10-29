// Shown while the free-tier backend is waking up (or unreachable).
// `status` is whatever your health check sets: "ok" | "unreachable" | anything else = checking.
export function WakeUpBanner({ status }) {
  if (status === "ok") return null;
  const unreachable = status === "unreachable";
  return (
    <div
      role="status"
      className={`border-b px-6 py-2 text-sm ${
        unreachable
          ? "border-red-300 bg-red-50 text-red-700"
          : "border-signal/40 bg-signal-light text-signal-dark"
      }`}
    >
      <div className="max-w-6xl mx-auto flex items-center gap-3 flex-wrap">
        <span className="font-medium">
          {unreachable ? "Can't reach the server." : "Waking up the server…"}
        </span>
        <span className="text-xs opacity-80">
          {unreachable
            ? "Check your connection and reload the page."
            : "The free-tier backend sleeps when idle, so the first request can take up to a minute. Everything works once this banner disappears."}
        </span>
      </div>
      {!unreachable && (
        <div className="max-w-6xl mx-auto mt-2 h-0.5 overflow-hidden bg-signal/20">
          <div
            className="h-full w-1/3 bg-signal"
            style={{ animation: "wake-slide 1.6s ease-in-out infinite" }}
          />
        </div>
      )}
    </div>
  );
}
