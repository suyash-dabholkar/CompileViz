import { useState } from "react";
import Ll1TableView from "../components/Ll1TableView";
import PresetPicker from "../components/PresetPicker";
import { Panel } from "../components/ui/Panel";
import { Button } from "../components/ui/Button";
import { GRAMMAR_PRESETS } from "../presets/presets";
import TraceViewer from "../components/TraceViewer";
import GrammarSteps from "../components/steps/GrammarSteps";
import { analyzeGrammar, fetchGrammarSteps } from "../api/grammarApi";
import { extractErrorMessage } from "../api/client";

const DEFAULT_GRAMMAR = `E -> T E'
E' -> + T E' | eps
T -> F T'
T' -> * F T' | eps
F -> ( E ) | id`;

export default function GrammarTool() {
  const [grammarText, setGrammarText] = useState(DEFAULT_GRAMMAR);
  const [result, setResult] = useState(null);
  const [trace, setTrace] = useState(null);
  const [mode, setMode] = useState("result");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleAnalyze(e) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const [data, steps] = await Promise.all([
        analyzeGrammar(grammarText),
        fetchGrammarSteps(grammarText),
      ]);
      setResult(data);
      setTrace(steps);
    } catch (err) {
      setError(extractErrorMessage(err));
      setResult(null);
      setTrace(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Grammar Analysis Tool</h1>
        <p className="text-ink-soft text-sm mt-1 max-w-2xl">
          Enter a context-free grammar (one rule per line, "-&gt;" or "::=", "|"
          for alternatives, "eps" or "\u03b5" for the empty production) and see
          its FIRST and FOLLOW sets and its LL(1) parsing table.
        </p>
      </header>

      <PresetPicker
        label="Preset grammars"
        presets={GRAMMAR_PRESETS}
        onSelect={(preset) => setGrammarText(preset.grammar)}
      />

      <form onSubmit={handleAnalyze} className="space-y-2">
        <textarea
          value={grammarText}
          onChange={(e) => setGrammarText(e.target.value)}
          rows={6}
          spellCheck={false}
          className="w-full border border-ink/25 bg-white px-3 py-2 font-mono text-sm focus:outline-none focus:border-blueprint"
        />
        <Button type="submit" disabled={loading || !grammarText.trim()}>
          {loading ? "Analyzing…" : "Analyze"}
        </Button>
      </form>

      {error && (
        <div className="border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {trace && (
        <div className="flex items-center gap-3">
          <div className="flex" role="tablist" aria-label="View">
            {[
              ["result", "Result"],
              ["teach", "Teach me"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={mode === id}
                onClick={() => setMode(id)}
                className={`-ml-px border px-3 py-1.5 font-mono text-xs uppercase tracking-wide transition-colors first:ml-0 ${
                  mode === id
                    ? "border-ink bg-ink text-paper"
                    : "border-graph bg-white text-ink-soft hover:bg-paper"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="text-xs text-ink-faint">
            {mode === "result"
              ? "The converged sets and the finished table."
              : `${trace.steps.length} steps. Arrow keys to walk it.`}
          </p>
        </div>
      )}

      {mode === "teach" && trace && (
        <TraceViewer key={grammarText} trace={trace}>
          {(props) => <GrammarSteps {...props} />}
        </TraceViewer>
      )}

      {mode === "result" && result && (
        <>
          <div
            className={`flex items-center gap-2 px-3 py-2 text-sm font-medium ${
              result.ll1_table.is_ll1 ? "bg-circuit-light text-circuit" : "bg-signal-light text-signal-dark"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${result.ll1_table.is_ll1 ? "bg-circuit" : "bg-signal-dark"}`}
            />
            {result.ll1_table.is_ll1
              ? "This grammar is LL(1)."
              : `Not LL(1): ${result.ll1_table.conflicts.length} conflict(s) found, highlighted below.`}
          </div>

          <Panel title="FIRST and FOLLOW sets" className="!p-0">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr>
                    <th className="px-4 py-2.5 text-left font-medium text-ink-soft border-b border-graph">
                      Non-terminal
                    </th>
                    <th className="px-4 py-2.5 text-left font-medium text-ink-soft border-b border-graph">
                      FIRST
                    </th>
                    <th className="px-4 py-2.5 text-left font-medium text-ink-soft border-b border-graph">
                      FOLLOW
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {result.non_terminals.map((nt) => (
                    <tr key={nt} className="odd:bg-white even:bg-paper/60">
                      <td className="px-4 py-2 font-mono font-medium text-ink border-b border-graph/60">
                        {nt}
                        {nt === result.start_symbol && (
                          <span className="ml-1.5 text-xs text-blueprint font-sans">(start)</span>
                        )}
                      </td>
                      <td className="px-4 py-2 font-mono text-ink-soft border-b border-graph/60">
                        {result.first_sets[nt].join(", ")}
                      </td>
                      <td className="px-4 py-2 font-mono text-ink-soft border-b border-graph/60">
                        {result.follow_sets[nt].join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="LL(1) parsing table">
            <Ll1TableView table={result.ll1_table} />
          </Panel>
        </>
      )}
    </div>
  );
}
