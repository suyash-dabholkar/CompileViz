import { useEffect, useState } from "react";
import apiClient from "./api/client";

// Milestone 1 placeholder. Real pages (RegexPlayground, GrammarTool,
// DfaMinimizer, CompilerDashboard) get added under src/pages/ in later
// milestones and wired up here, likely with a simple tab or router.
function App() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    apiClient
      .get("/health")
      .then((res) => setStatus(res.data.status))
      .catch(() => setStatus("backend unreachable"));
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-slate-50">
      <h1 className="text-3xl font-bold text-slate-800">CompileViz</h1>
      <p className="text-slate-600">
        Backend status: <span className="font-mono">{status}</span>
      </p>
    </div>
  );
}

export default App;
