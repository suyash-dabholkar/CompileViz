import { useState } from "react";
import DfaGraph from "../components/DfaGraph";
import PresetPicker from "../components/PresetPicker";
import { Panel } from "../components/ui/Panel";
import { Button } from "../components/ui/Button";
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
        <h1 className="text-2xl font-semibold text-ink">Regex-to-Automata Playground</h1>
        <p className="text-ink-soft text-sm mt-1 max-w-2xl">
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
          className="flex-1 border border-ink/25 bg-white px-3 py-2 font-mono text-sm focus:outline-none focus:border-blueprint"
        />
        <Button type="submit" disabled={loading || !pattern.trim()}>
          {loading ? "Building…" : "Build"}
        </Button>
      </form>

      {error && (
        <div className="border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {comparison && (
        <Panel variant="quiet" className="!p-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-graph">
            <div className="p-4">
              <p className="text-sm text-ink-soft">Direct method (followpos)</p>
              <p className="font-mono text-2xl text-blueprint mt-1">
                {comparison.direct_method.state_count}
                <span className="text-sm text-ink-faint font-sans ml-1.5">states</span>
              </p>
              <p className="text-xs text-ink-faint mt-1">
                avg build time {(comparison.direct_method.avg_build_time_seconds * 1000).toFixed(3)} ms
              </p>
            </div>
            <div className="p-4">
              <p className="text-sm text-ink-soft">Indirect method (Thompson + subset)</p>
              <p className="font-mono text-2xl text-blueprint mt-1">
                {comparison.indirect_method.state_count}
                <span className="text-sm text-ink-faint font-sans ml-1.5">states</span>
              </p>
              <p className="text-xs text-ink-faint mt-1">
                avg build time {(comparison.indirect_method.avg_build_time_seconds * 1000).toFixed(3)} ms
              </p>
            </div>
          </div>
        </Panel>
      )}

      {(directDfa || indirectDfa) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Panel title="Direct method DFA">
            <DfaGraph dfa={directDfa} />
          </Panel>
          <Panel title="Indirect method DFA">
            <DfaGraph dfa={indirectDfa} />
          </Panel>
        </div>
      )}

      {directDfa && (
        <form onSubmit={handleTestString} className="flex items-end gap-2">
          <div className="flex-1">
            <label className="block text-xs font-medium text-ink-soft mb-1">
              Test a string against this pattern
            </label>
            <input
              type="text"
              value={testText}
              onChange={(e) => setTestText(e.target.value)}
              className="w-full border border-ink/25 bg-white px-3 py-2 font-mono text-sm focus:outline-none focus:border-blueprint"
            />
          </div>
          <Button type="submit" variant="secondary">
            Test
          </Button>
        </form>
      )}

      {matchResult && (
        <div
          className={`inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium ${
            matchResult.matches ? "bg-circuit-light text-circuit" : "bg-red-50 text-red-700"
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${matchResult.matches ? "bg-circuit" : "bg-red-600"}`} />
          {matchResult.matches ? "Matches" : "Does not match"}
        </div>
      )}
    </div>
  );
}
