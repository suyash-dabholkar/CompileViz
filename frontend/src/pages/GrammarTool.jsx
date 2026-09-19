import { useState } from "react";
import Ll1TableView from "../components/Ll1TableView";
import PresetPicker from "../components/PresetPicker";
import { GRAMMAR_PRESETS } from "../presets/presets";
import { analyzeGrammar } from "../api/grammarApi";
import { extractErrorMessage } from "../api/client";

const DEFAULT_GRAMMAR = `E -> T E'
E' -> + T E' | eps
T -> F T'
T' -> * F T' | eps
F -> ( E ) | id`;

export default function GrammarTool() {
  const [grammarText, setGrammarText] = useState(DEFAULT_GRAMMAR);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleAnalyze(e) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeGrammar(grammarText);
      setResult(data);
    } catch (err) {
      setError(extractErrorMessage(err));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-800">Grammar Analysis Tool</h1>
        <p className="text-slate-600 text-sm mt-1">
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
          className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          type="submit"
          disabled={loading || !grammarText.trim()}
          className="rounded-md bg-blue-700 px-4 py-2 text-white font-medium disabled:opacity-50"
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </form>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <>
          <div
            className={`rounded-md px-3 py-2 text-sm font-medium ${
              result.ll1_table.is_ll1
                ? "bg-green-100 text-green-800"
                : "bg-red-100 text-red-800"
            }`}
          >
            {result.ll1_table.is_ll1
              ? "This grammar is LL(1)."
              : `Not LL(1): ${result.ll1_table.conflicts.length} conflict(s) found, highlighted below.`}
          </div>

          <div>
            <h2 className="font-semibold text-slate-700 mb-2">
              FIRST and FOLLOW sets
            </h2>
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                      Non-terminal
                    </th>
                    <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                      FIRST
                    </th>
                    <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                      FOLLOW
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {result.non_terminals.map((nt) => (
                    <tr key={nt} className="odd:bg-white even:bg-slate-50">
                      <td className="px-3 py-2 font-mono font-semibold text-slate-800 border-b border-slate-100">
                        {nt}
                        {nt === result.start_symbol && (
                          <span className="ml-1 text-xs text-blue-600">(start)</span>
                        )}
                      </td>
                      <td className="px-3 py-2 font-mono text-slate-700 border-b border-slate-100">
                        {result.first_sets[nt].join(", ")}
                      </td>
                      <td className="px-3 py-2 font-mono text-slate-700 border-b border-slate-100">
                        {result.follow_sets[nt].join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h2 className="font-semibold text-slate-700 mb-2">LL(1) parsing table</h2>
            <Ll1TableView table={result.ll1_table} />
          </div>
        </>
      )}
    </div>
  );
}
