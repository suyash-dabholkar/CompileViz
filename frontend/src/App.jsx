import { useEffect, useState } from "react";
import apiClient from "./api/client";
import RegexPlayground from "./pages/RegexPlayground";

// Milestone 4: the regex playground is the first real page. As more
// pages are added (grammar tool, DFA minimizer, compiler dashboard),
// this is where simple tab navigation gets introduced, one page is
// still simple enough not to need a router yet.
function App() {
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

  return (
    <div className="min-h-screen bg-slate-50">
      <RegexPlayground />
      <footer className="text-center text-xs text-slate-400 pb-4">
        backend: <span className="font-mono">{backendStatus}</span>
      </footer>
    </div>
  );
}

export default App;
