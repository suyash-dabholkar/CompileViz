import { useState } from "react";
import DfaGraph from "../components/DfaGraph";
import PresetPicker from "../components/PresetPicker";
import { REGEX_PRESETS } from "../presets/presets";
import { minimizeDfa } from "../api/minimizeApi";
import { extractErrorMessage } from "../api/client";

const DEFAULT_PATTERN = "(a|b)*abb";

function PartitionTrace({ trace }) {
  return (
    <ol className="space-y-2 text-sm">
      {trace.map((round, i) => {
        const isLast = i === trace.length - 1;
        const isStable = isLast && trace.length > 1 && JSON.stringify(round) === JSON.stringify(trace[i - 1]);
        return (
          <li key={i} className="font-mono">
            <span className="text-slate-500 mr-2">
              {i === 0 ? "Initial split:" : `Round ${i}:`}
              {isStable ? " (stable, no further splits)" : ""}
            </span>
            {round.map((group, gi) => (
              <span
                key={gi}
                className={`inline-block mx-1 px-2 py-0.5 rounded ${
                  group.length > 1 ? "bg-blue-100 text-blue-800" : "bg-slate-100 text-slate-600"
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
        <h1 className="text-2xl font-bold text-slate-800">DFA Minimizer</h1>
        <p className="text-slate-600 text-sm mt-1">
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
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Pattern
          </label>
          <input
            type="text"
            value={pattern}
            onChange={(e) => setPattern(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Method
          </label>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="indirect">Indirect (Thompson + subset)</option>
            <option value="direct">Direct (followpos)</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={loading || !pattern.trim()}
          className="rounded-md bg-blue-700 px-4 py-2 text-white font-medium disabled:opacity-50"
        >
          {loading ? "Minimizing..." : "Minimize"}
        </button>
      </form>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <>
          <div className="grid grid-cols-2 gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
            <div>
              <p className="font-semibold text-slate-700">Before minimization</p>
              <p className="text-slate-600">{result.original.num_states} states</p>
            </div>
            <div>
              <p className="font-semibold text-slate-700">After minimization</p>
              <p className="text-slate-600">
                {result.minimized.num_states} states
                {result.original.num_states !== result.minimized.num_states && (
                  <span className="ml-2 text-green-700 font-medium">
                    ({result.original.num_states - result.minimized.num_states} merged away)
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <h2 className="font-semibold text-slate-700 mb-2">Original DFA</h2>
              <DfaGraph dfa={result.original} />
            </div>
            <div>
              <h2 className="font-semibold text-slate-700 mb-2">Minimized DFA</h2>
              <DfaGraph dfa={result.minimized} />
            </div>
          </div>

          <div>
            <h2 className="font-semibold text-slate-700 mb-2">
              Partition refinement trace
            </h2>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <PartitionTrace trace={result.partition_trace} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
