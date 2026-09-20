import { useEffect, useState } from "react";
import apiClient from "./api/client";
import { Logomark } from "./components/ui/Logomark";
import RegexPlayground from "./pages/RegexPlayground";
import GrammarTool from "./pages/GrammarTool";
import DfaMinimizer from "./pages/DfaMinimizer";
import CompilerPipeline from "./pages/CompilerPipeline";

const TABS = [
  { id: "regex", label: "Regex Playground", Component: RegexPlayground },
  { id: "grammar", label: "Grammar Tool", Component: GrammarTool },
  { id: "minimizer", label: "DFA Minimizer", Component: DfaMinimizer },
  { id: "compiler", label: "Compiler Pipeline", Component: CompilerPipeline },
];

function App() {
  const [activeTab, setActiveTab] = useState(TABS[0].id);
  const [backendStatus, setBackendStatus] = useState("checking");

  useEffect(() => {
    let cancelled = false;

    async function checkHealth(retriesLeft) {
      try {
        const res = await apiClient.get("/health");
        if (!cancelled) setBackendStatus(res.data.status);
      } catch {
        if (retriesLeft > 0) {
          // A cold-started backend (first request after `uvicorn --reload`
          // starts, or a free-tier host waking up once deployed) can miss
          // the very first request. One retry after a short delay avoids
          // permanently showing "unreachable" for what was really just
          // bad timing.
          setTimeout(() => checkHealth(retriesLeft - 1), 1500);
        } else if (!cancelled) {
          setBackendStatus("unreachable");
        }
      }
    }

    checkHealth(2);
    return () => {
      cancelled = true;
    };
  }, []);

  const ActiveComponent = TABS.find((t) => t.id === activeTab).Component;
  const statusColor =
    backendStatus === "ok" ? "bg-circuit" : backendStatus === "unreachable" ? "bg-red-500" : "bg-signal";

  return (
    <div className="min-h-screen font-sans">
      <header className="border-b border-ink/15 bg-paper/90 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 pt-5 pb-0">
          <div className="flex items-center gap-3">
            <Logomark className="w-9 h-5 text-blueprint" />
            <div>
              <h1 className="font-sans font-semibold text-lg leading-none text-ink">CompileViz</h1>
              <p className="text-xs text-ink-faint mt-1">
                Regex to automata, grammars, and a working toy compiler, all live
              </p>
            </div>
          </div>

          <nav className="flex gap-6 mt-5">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative pb-3 text-sm font-medium transition-colors ${
                  activeTab === tab.id ? "text-ink" : "text-ink-faint hover:text-ink-soft"
                }`}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <span className="absolute left-0 right-0 -bottom-px h-0.5 bg-signal" />
                )}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <ActiveComponent />

      <footer className="max-w-6xl mx-auto px-6 pb-6 pt-2 flex items-center gap-2">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${statusColor}`} />
        <span className="text-xs text-ink-faint font-mono">backend: {backendStatus}</span>
      </footer>
    </div>
  );
}

export default App;

