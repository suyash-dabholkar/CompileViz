import { Logomark } from "./Logomark";

const ICONS = {
  regex: (
    <path d="M4 7h4m-2-2v4M11 16l6-8M11 8l6 8M19 17h.01" strokeLinecap="round" />
  ),
  grammar: (
    <path d="M12 4v5m0 0l-6 5m6-5l6 5M6 14v4m12-4v4M4 18h4m8 0h4" strokeLinecap="round" strokeLinejoin="round" />
  ),
  minimizer: (
    <path d="M4 6h7v5H4zM13 13h7v5h-7zM11 8.5h3.5V13" strokeLinecap="round" strokeLinejoin="round" />
  ),
  compiler: (
    <path d="M8 7l-5 5 5 5M16 7l5 5-5 5M14 5l-4 14" strokeLinecap="round" strokeLinejoin="round" />
  ),
};

function NavIcon({ name }) {
  return (
    <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] shrink-0" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}

const ITEM_H = 44; // px, keep in sync with h-11 below

export function Sidebar({ tabs, active, onSelect, status, open, onClose }) {
  const index = Math.max(0, tabs.findIndex((t) => t.id === active));
  const dot =
    status === "ok" ? "bg-circuit" : status === "unreachable" ? "bg-red-500" : "bg-signal animate-pulse";
  const statusText =
    status === "ok" ? "Backend online" : status === "unreachable" ? "Backend offline" : "Waking backend…";

  return (
    <>
      {/* mobile scrim */}
      <div
        onClick={onClose}
        className={`fixed inset-0 z-30 bg-ink/50 backdrop-blur-sm transition-opacity lg:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <aside
        className={`fixed lg:sticky top-0 left-0 z-40 h-screen w-64 shrink-0 flex flex-col bg-ink text-white
          transition-transform duration-300 ease-out lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="sidebar-grid absolute inset-0 pointer-events-none" />

        <div className="relative px-5 pt-6 pb-5 flex items-center gap-3">
          <Logomark className="w-10 h-6 text-signal logo-flow" />
          <div>
            <h1 className="font-semibold text-lg leading-none tracking-tight">CompileViz</h1>
            <p className="text-[11px] text-white/50 mt-1.5 font-mono">compiler design lab</p>
          </div>
        </div>

        <p className="relative px-5 pt-3 pb-2 text-[10px] uppercase tracking-[0.18em] text-white/40 font-mono">
          Tools
        </p>

        <nav className="relative px-3">
          {/* sliding highlight */}
          <span
            aria-hidden="true"
            className="absolute left-3 right-3 h-11 rounded-md bg-white/10 border border-white/10 transition-transform duration-300 ease-[cubic-bezier(.4,1.3,.5,1)]"
            style={{ transform: `translateY(${index * ITEM_H}px)` }}
          />
          <span
            aria-hidden="true"
            className="absolute left-3 w-[3px] h-6 mt-[10px] rounded-full bg-signal transition-transform duration-300 ease-[cubic-bezier(.4,1.3,.5,1)]"
            style={{ transform: `translateY(${index * ITEM_H}px)` }}
          />
          {tabs.map((tab, i) => {
            const on = tab.id === active;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  onSelect(tab.id);
                  onClose();
                }}
                className={`relative group w-full h-11 flex items-center gap-3 pl-5 pr-3 rounded-md text-sm font-medium text-left transition-colors ${
                  on ? "text-white" : "text-white/60 hover:text-white"
                }`}
              >
                <span className={`transition-transform duration-200 group-hover:scale-110 ${on ? "text-signal" : ""}`}>
                  <NavIcon name={tab.icon} />
                </span>
                <span className="flex-1">{tab.label}</span>
                <kbd className="hidden xl:block text-[10px] font-mono text-white/30 group-hover:text-white/60">
                  Alt+{i + 1}
                </kbd>
              </button>
            );
          })}
        </nav>

        <div className="relative mt-auto p-4">
          <div className="rounded-md border border-white/10 bg-white/5 px-3 py-2.5 flex items-center gap-2.5">
            <span className={`w-2 h-2 rounded-full ${dot}`} />
            <span className="text-xs text-white/70 font-mono">{statusText}</span>
          </div>
          <p className="mt-3 text-[10px] text-white/30 font-mono text-center">BCSE307P · VIT Vellore</p>
        </div>
      </aside>
    </>
  );
}
