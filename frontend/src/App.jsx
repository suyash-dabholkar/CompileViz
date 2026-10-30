import { useEffect, useState } from "react";
import apiClient from "./api/client";
import { Sidebar } from "./components/ui/Sidebar";
import { WakeUpBanner } from "./components/ui/WakeUpBanner";
import { Logomark } from "./components/ui/Logomark";
import RegexPlayground from "./pages/RegexPlayground";
import GrammarTool from "./pages/GrammarTool";
import DfaMinimizer from "./pages/DfaMinimizer";
import CompilerPipeline from "./pages/CompilerPipeline";

const TABS = [
  { id: "regex", label: "Regex Playground", icon: "regex", Component: RegexPlayground },
  { id: "grammar", label: "Grammar Tool", icon: "grammar", Component: GrammarTool },
  { id: "minimizer", label: "DFA Minimizer", icon: "minimizer", Component: DfaMinimizer },
  { id: "compiler", label: "Compiler Pipeline", icon: "compiler", Component: CompilerPipeline },
];

function loadTab() {
  try {
    const t = localStorage.getItem("cv-tab");
    if (TABS.some((x) => x.id === t)) return t;
  } catch {}
  return TABS[0].id;
}

function App() {
  const [activeTab, setActiveTab] = useState(loadTab);
  const [backendStatus, setBackendStatus] = useState("checking");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    try { localStorage.setItem("cv-tab", activeTab); } catch {}
  }, [activeTab]);

  // Alt+1..4 switches tools
  useEffect(() => {
    const onKey = (e) => {
      if (!e.altKey) return;
      const i = Number(e.key) - 1;
      if (TABS[i]) { e.preventDefault(); setActiveTab(TABS[i].id); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Health check: keeps retrying ~1 min so a sleeping free-tier backend can wake up.
  useEffect(() => {
    let cancelled = false;
    async function checkHealth(retriesLeft) {
      try {
        const res = await apiClient.get("/health");
        if (!cancelled) setBackendStatus(res.data.status);
      } catch {
        if (retriesLeft > 0) setTimeout(() => checkHealth(retriesLeft - 1), 3000);
        else if (!cancelled) setBackendStatus("unreachable");
      }
    }
    checkHealth(20);
    return () => { cancelled = true; };
  }, []);

  const ActiveComponent = TABS.find((t) => t.id === activeTab).Component;
  const activeLabel = TABS.find((t) => t.id === activeTab).label;

  return (
    <div className="min-h-screen font-sans flex">
      <Sidebar
        tabs={TABS}
        active={activeTab}
        onSelect={setActiveTab}
        status={backendStatus}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
      />

      <div className="flex-1 min-w-0 flex flex-col">
        {/* mobile top bar */}
        <div className="lg:hidden sticky top-0 z-20 flex items-center gap-3 px-4 h-14 bg-ink text-white">
          <button onClick={() => setMenuOpen(true)} aria-label="Open menu" className="p-1">
            <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
            </svg>
          </button>
          <Logomark className="w-8 h-5 text-signal" />
          <span className="font-semibold">{activeLabel}</span>
        </div>

        <WakeUpBanner status={backendStatus} />

        <main key={activeTab} className="page-enter flex-1">
          <ActiveComponent />
        </main>
      </div>
    </div>
  );
}

export default App;
