import { useState } from "react";
import DfaGraph from "../components/DfaGraph";
import PresetPicker from "../components/PresetPicker";
import { Panel } from "../components/ui/Panel";
import { Button } from "../components/ui/Button";
import { REGEX_PRESETS } from "../presets/presets";
import { minimizeDfa } from "../api/minimizeApi";
import { extractErrorMessage } from "../api/client";

const DEFAULT_PATTERN = "(a|b)*abb";

function PartitionTrace({ trace }) {
  return (
    <ol className="space-y-2.5 text-sm">
      {trace.map((round, i) => {
        const isLast = i === trace.length - 1;
        const isStable = isLast && trace.length > 1 && JSON.stringify(round) === JSON.stringify(trace[i - 1]);
        return (
          <li key={i} className="font-mono">
            <span className="text-ink-faint mr-2 font-sans">
              {i === 0 ? "Initial split:" : `Round ${i}:`}
              {isStable ? " (stable, no further splits)" : ""}
            </span>
            {round.map((group, gi) => (
              <span
                key={gi}
                className={`inline-block mx-1 px-2 py-0.5 ${
                  group.length > 1 ? "bg-blueprint-light text-blueprint" : "bg-paper text-ink-faint"
                }`}
              >
                {"{"}
                {group.join(", ")}
                {"}"}
              </span>
            ))}
          </li>
        );
      })}
    </ol>
  );
}

export default function DfaMinimizer() {
  const [pattern, setPattern] = useState(DEFAULT_PATTERN);
  const [method, setMethod] = useState("indirect");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleMinimize(e) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await minimizeDfa(pattern, method);
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
        <h1 className="text-2xl font-semibold text-ink">DFA Minimizer</h1>
        <p className="text-ink-soft text-sm mt-1 max-w-2xl">
          Enter a regex, build its DFA, and minimize it with partition
          refinement. Try the indirect method on a pattern with a wide
          character class, its raw DFA is usually far from minimal.
        </p>
      </header>

      <PresetPicker
        label="Preset regexes"
        presets={REGEX_PRESETS}
        onSelect={(preset) => setPattern(preset.pattern)}
      />

      <form onSubmit={handleMinimize} className="flex gap-2 items-end">
        <div className="flex-1">
          <label className="block text-xs font-medium text-ink-soft mb-1">Pattern</label>
          <input
            type="text"
            value={pattern}
            onChange={(e) => setPattern(e.target.value)}
            className="w-full border border-ink/25 bg-white px-3 py-2 font-mono text-sm focus:outline-none focus:border-blueprint"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-ink-soft mb-1">Method</label>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="border border-ink/25 bg-white px-3 py-2 text-sm text-ink-soft focus:outline-none focus:border-blueprint"
          >
            <option value="indirect">Indirect (Thompson + subset)</option>
            <option value="direct">Direct (followpos)</option>
          </select>
        </div>
        <Button type="submit" disabled={loading || !pattern.trim()}>
          {loading ? "Minimizing…" : "Minimize"}
        </Button>
      </form>

      {error && (
        <div className="border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <>
          <Panel variant="quiet" className="!p-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-graph">
              <div className="p-4">
                <p className="text-sm text-ink-soft">Before minimization</p>
                <p className="font-mono text-2xl text-blueprint mt-1">
                  {result.original.num_states}
                  <span className="text-sm text-ink-faint font-sans ml-1.5">states</span>
                </p>
              </div>
              <div className="p-4">
                <p className="text-sm text-ink-soft">After minimization</p>
                <p className="font-mono text-2xl text-blueprint mt-1">
                  {result.minimized.num_states}
                  <span className="text-sm text-ink-faint font-sans ml-1.5">states</span>
                  {result.original.num_states !== result.minimized.num_states && (
                    <span className="ml-2 text-sm text-circuit font-sans font-medium">
                      ({result.original.num_states - result.minimized.num_states} merged away)
                    </span>
                  )}
                </p>
              </div>
            </div>
          </Panel>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Panel title="Original DFA">
              <DfaGraph dfa={result.original} />
            </Panel>
            <Panel title="Minimized DFA">
              <DfaGraph dfa={result.minimized} />
            </Panel>
          </div>

          <Panel title="Partition refinement trace">
            <PartitionTrace trace={result.partition_trace} />
          </Panel>
        </>
      )}
    </div>
  );
}
