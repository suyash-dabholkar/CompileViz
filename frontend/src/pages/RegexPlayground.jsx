import { useState } from "react";
import DfaGraph from "../components/DfaGraph";
import PresetPicker from "../components/PresetPicker";
import { REGEX_PRESETS } from "../presets/presets";
import {
  buildDirectDfa,
  buildIndirectDfa,
  compareMethods,
  extractErrorMessage,
  matchPattern,
} from "../api/regexApi";

const DEFAULT_PATTERN = "(a|b)*abb";

export default function RegexPlayground() {
  const [pattern, setPattern] = useState(DEFAULT_PATTERN);
  const [directDfa, setDirectDfa] = useState(null);
  const [indirectDfa, setIndirectDfa] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [testText, setTestText] = useState("");
  const [matchResult, setMatchResult] = useState(null);

  async function handleBuild(e) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    setMatchResult(null);
    try {
      const [direct, indirect, compare] = await Promise.all([
        buildDirectDfa(pattern),
        buildIndirectDfa(pattern),
        compareMethods(pattern),
      ]);
      setDirectDfa(direct);
      setIndirectDfa(indirect);
      setComparison(compare);
    } catch (err) {
      setError(extractErrorMessage(err));
      setDirectDfa(null);
      setIndirectDfa(null);
      setComparison(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleTestString(e) {
    e.preventDefault();
    try {
      const result = await matchPattern(pattern, testText, "direct");
      setMatchResult(result);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-800">
          Regex-to-Automata Playground
        </h1>
        <p className="text-slate-600 text-sm mt-1">
          Enter a regex and see it converted to a DFA two ways: the direct
          method (followpos) and the indirect method (Thompson + subset
          construction).
        </p>
      </header>

      <PresetPicker
        label="Preset regexes"
        presets={REGEX_PRESETS}
        onSelect={(preset) => setPattern(preset.pattern)}
      />

      <form onSubmit={handleBuild} className="flex gap-2">
        <input
          type="text"
          value={pattern}
          onChange={(e) => setPattern(e.target.value)}
          placeholder="e.g. [a-zA-Z][a-zA-Z0-9]*"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          type="submit"
          disabled={loading || !pattern.trim()}
          className="rounded-md bg-blue-700 px-4 py-2 text-white font-medium disabled:opacity-50"
        >
          {loading ? "Building..." : "Build"}
        </button>
      </form>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {comparison && (
        <div className="grid grid-cols-2 gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
          <div>
            <p className="font-semibold text-slate-700">Direct method (followpos)</p>
            <p className="text-slate-600">
              {comparison.direct_method.state_count} states, avg build time{" "}
              {(comparison.direct_method.avg_build_time_seconds * 1000).toFixed(3)} ms
            </p>
          </div>
          <div>
            <p className="font-semibold text-slate-700">
              Indirect method (Thompson + subset)
            </p>
            <p className="text-slate-600">
              {comparison.indirect_method.state_count} states, avg build time{" "}
              {(comparison.indirect_method.avg_build_time_seconds * 1000).toFixed(3)} ms
            </p>
          </div>
        </div>
      )}

      {(directDfa || indirectDfa) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <h2 className="font-semibold text-slate-700 mb-2">
              Direct method DFA
            </h2>
            <DfaGraph dfa={directDfa} />
          </div>
          <div>
            <h2 className="font-semibold text-slate-700 mb-2">
              Indirect method DFA
            </h2>
            <DfaGraph dfa={indirectDfa} />
          </div>
        </div>
      )}

      {directDfa && (
        <form onSubmit={handleTestString} className="flex items-end gap-2">
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Test a string against this pattern
            </label>
            <input
              type="text"
              value={testText}
              onChange={(e) => setTestText(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <button
            type="submit"
            className="rounded-md bg-slate-700 px-4 py-2 text-white font-medium"
          >
            Test
          </button>
        </form>
      )}

      {matchResult && (
        <div
          className={`inline-block rounded-md px-3 py-1 text-sm font-medium ${
            matchResult.matches
              ? "bg-green-100 text-green-800"
              : "bg-red-100 text-red-800"
          }`}
        >
          {matchResult.matches ? "Matches" : "Does not match"}
        </div>
      )}
    </div>
  );
}
