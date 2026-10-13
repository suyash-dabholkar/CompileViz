import { useMemo } from "react";
import DfaGraph from "../DfaGraph";
import { Panel } from "../ui/Panel";

/**
 * Draws one round of partition refinement.
 *
 * The live partition is folded from the steps rather than read from
 * `partition_trace`, because that trace only records the partition at
 * the end of each round. Refinement happens group by group, and watching
 * one group split while the others sit untouched is the part the
 * round-by-round summary cannot show.
 */

const fmt = (values) => (values?.length ? `{${values.join(", ")}}` : "{}");
const sameSet = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

function accumulate(steps, index) {
  let partition = [];
  const merged = {}; // minimized state -> original states
  // The groups to mark as current. On a split this is the buckets the
  // group became, not the group it was: by the time the step is on
  // screen the original is gone from the partition, so highlighting it
  // would highlight nothing at all.
  let currentGroups = [];

  for (let i = 0; i <= index && i < steps.length; i += 1) {
    const { kind, data } = steps[i];

    if (kind === "min.init" || kind === "min.sweep" || kind === "min.stable") {
      partition = data.groups.map((g) => [...g]);
      currentGroups = [];
    } else if (kind === "min.group") {
      currentGroups = data.groups;
      // Splice this group's buckets in where the group used to be, so
      // the partition refines in place as the round walks through it.
      const at = partition.findIndex((g) => sameSet(g, data.group));
      if (at >= 0) partition.splice(at, 1, ...data.groups.map((g) => [...g]));
    } else if (kind === "min.merge") {
      merged[data.minimized_state] = data.result;
      currentGroups = [data.result];
    }
  }

  return { partition, merged, currentGroups };
}

export default function MinimizeSteps({ step, index, steps, context }) {
  const acc = useMemo(() => accumulate(steps, index), [steps, index]);

  const alphabet = context.original?.alphabet ?? [];
  const signatures = step.data.signatures;
  const distinguishers = step.data.distinguishers ?? [];
  const mergedStates = Object.keys(acc.merged).map(Number).sort((a, b) => a - b);

  return (
    <div className="space-y-4">
      <Panel title="Current partition" variant="quiet">
        <div className="flex flex-wrap items-center gap-2">
          {acc.partition.map((group) => {
            const isCurrent = acc.currentGroups.some((g) => sameSet(group, g));
            return (
              <span
                key={group.join(",")}
                className={`border px-2.5 py-1 font-mono text-sm ${
                  isCurrent
                    ? "border-signal bg-signal-light text-ink"
                    : group.length > 1
                      ? "border-blueprint/40 bg-blueprint-light text-blueprint"
                      : "border-graph bg-white text-ink-faint"
                }`}
              >
                {fmt(group)}
              </span>
            );
          })}
          <span className="ml-1 font-mono text-xs text-ink-faint">
            {acc.partition.length} group{acc.partition.length === 1 ? "" : "s"}
          </span>
        </div>
      </Panel>

      {signatures && (
        <Panel
          title="Signatures"
          subtitle={
            distinguishers.length
              ? `split by ${distinguishers.join(", ")}`
              : "all identical"
          }
          variant="quiet"
          className="!p-0"
        >
          <table className="w-full text-left font-mono text-sm">
            <thead>
              <tr className="border-b border-graph text-xs uppercase tracking-wide text-ink-faint">
                <th className="px-4 py-2 font-medium">state</th>
                {alphabet.map((symbol) => (
                  <th
                    key={symbol}
                    className={`px-3 py-2 font-medium ${
                      distinguishers.includes(symbol) ? "bg-signal-light text-ink" : ""
                    }`}
                  >
                    on {symbol}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(signatures).map(([state, row]) => (
                <tr key={state} className="border-b border-graph/60 last:border-b-0">
                  <td className="px-4 py-1.5 font-medium text-blueprint">q{state}</td>
                  {alphabet.map((symbol) => (
                    <td
                      key={symbol}
                      className={`px-3 py-1.5 text-ink-soft ${
                        distinguishers.includes(symbol) ? "bg-signal-light" : ""
                      }`}
                    >
                      {row[symbol]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="border-t border-graph px-4 py-2 text-xs text-ink-faint">
            G<em>n</em> is the group a transition lands in. Two states belong
            together only while every column agrees.
          </p>
        </Panel>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel
          title="Original DFA"
          subtitle={`${context.original?.num_states ?? "?"} states`}
        >
          <DfaGraph
            dfa={context.original}
            highlight={{ states: step.highlight.states }}
          />
        </Panel>

        {mergedStates.length > 0 ? (
          <Panel
            title="Minimized DFA"
            subtitle={`${mergedStates.length} of ${context.minimized?.num_states ?? "?"} states built`}
          >
            <DfaGraph
              dfa={context.minimized}
              highlight={{
                states:
                  step.data.minimized_state === undefined
                    ? []
                    : [step.data.minimized_state],
                discovered: mergedStates,
              }}
            />
          </Panel>
        ) : (
          <Panel title="Minimized DFA" variant="quiet">
            <p className="text-sm text-ink-faint">
              Nothing to build yet. Once the partition stops changing, each
              remaining group collapses into one state here.
            </p>
          </Panel>
        )}
      </div>
    </div>
  );
}
