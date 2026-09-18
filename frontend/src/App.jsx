import { useEffect, useState } from "react";
import apiClient from "./api/client";
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
  const [backendStatus, setBackendStatus] = useState("checking...");

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

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-white border-b border-slate-200 px-6">
        <div className="max-w-6xl mx-auto flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-blue-700 text-blue-700"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <ActiveComponent />

      <footer className="text-center text-xs text-slate-400 pb-4">
        backend: <span className="font-mono">{backendStatus}</span>
      </footer>
    </div>
  );
}

export default App;
