import { useState } from "react";
import DfaGraph from "../components/DfaGraph";
import PresetPicker from "../components/PresetPicker";
import TraceViewer from "../components/TraceViewer";
import RegexDirectSteps from "../components/steps/RegexDirectSteps";
import RegexIndirectSteps from "../components/steps/RegexIndirectSteps";
import { Panel } from "../components/ui/Panel";
import { Button } from "../components/ui/Button";
import { REGEX_PRESETS } from "../presets/presets";
import {
  buildDirectDfa,
  buildIndirectDfa,
  compareMethods,
  extractErrorMessage,
  fetchRegexSteps,
  matchPattern,
} from "../api/regexApi";

const DEFAULT_PATTERN = "(a|b)*abb";

export default function RegexPlayground() {
  const [pattern, setPattern] = useState(DEFAULT_PATTERN);
  const [directDfa, setDirectDfa] = useState(null);
  const [indirectDfa, setIndirectDfa] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [traces, setTraces] = useState(null);
  const [mode, setMode] = useState("result");
  const [teachMethod, setTeachMethod] = useState("direct");
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
      const [direct, indirect, compare, directSteps, indirectSteps] =
        await Promise.all([
          buildDirectDfa(pattern),
          buildIndirectDfa(pattern),
          compareMethods(pattern),
          fetchRegexSteps(pattern, "direct"),
          fetchRegexSteps(pattern, "indirect"),
        ]);
      setDirectDfa(direct);
      setIndirectDfa(indirect);
      setComparison(compare);
      // Both traces up front, in the same round trip as everything else:
      // switching method is then instant, with no second spinner and no
      // extra loading state to keep in sync.
      setTraces({ direct: directSteps, indirect: indirectSteps });
    } catch (err) {
      setError(extractErrorMessage(err));
      setDirectDfa(null);
      setIndirectDfa(null);
      setComparison(null);
      setTraces(null);
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

      {traces && (
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
              ? "The finished DFAs, both methods side by side."
              : "One step at a time. Arrow keys to walk it."}
          </p>
        </div>
      )}

      {mode === "teach" && traces && (
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex" role="tablist" aria-label="Construction method">
            {[
              ["direct", "Direct (followpos)"],
              ["indirect", "Indirect (Thompson + subset)"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={teachMethod === id}
                onClick={() => setTeachMethod(id)}
                className={`-ml-px border px-3 py-1.5 text-xs transition-colors first:ml-0 ${
                  teachMethod === id
                    ? "border-blueprint bg-blueprint-light text-blueprint"
                    : "border-graph bg-white text-ink-soft hover:bg-paper"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="text-xs text-ink-faint">
            {traces[teachMethod].steps.length} steps
          </p>
        </div>
      )}

      {mode === "teach" && traces && (
        // Keyed so switching pattern or method remounts cleanly rather
        // than carrying over a step index and quiz answers from the
        // trace that was on screen a moment ago.
        <TraceViewer key={`${pattern}-${teachMethod}`} trace={traces[teachMethod]}>
          {(props) =>
            teachMethod === "direct" ? (
              <RegexDirectSteps {...props} />
            ) : (
              <RegexIndirectSteps {...props} />
            )
          }
        </TraceViewer>
      )}

      {mode === "result" && comparison && (
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

      {mode === "result" && (directDfa || indirectDfa) && (
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
