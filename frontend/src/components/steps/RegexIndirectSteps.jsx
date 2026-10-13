import { useMemo } from "react";
import AstTreeView from "../AstTreeView";
import DfaGraph from "../DfaGraph";
import { Panel } from "../ui/Panel";

/**
 * Draws one step of the indirect construction: Thompson's NFA, then
 * subset construction turning it into a DFA.
 *
 * The NFA is rendered through DfaGraph rather than a second graph
 * component. Thompson's construction guarantees exactly one accept
 * state, so adapting the shape is a one-line map and the layout, styling
 * and highlighting all come for free.
 *
 * One thing to know about the highlight split: a step's
 * `highlight.states` always means NFA states (a fragment's states during
 * the nfa phase, the current subset during the subset phase), because
 * that is the set the student is reasoning about. The DFA graph's
 * highlight is derived from `step.data` instead, where the DFA indices
 * live.
 */

const fmt = (values) => (values?.length ? `{${values.join(", ")}}` : "{}");

/** Thompson fragments always have a single accept state, which is what
 *  lets DfaGraph render an NFA unchanged. */
const asGraph = (nfa) => nfa && { ...nfa, accepting: [nfa.accept] };

function accumulate(steps, index) {
  const nfaStates = new Set();
  const nfaEdges = new Set();
  const dfaStates = {}; // DFA index -> the NFA states it stands for
  const accepting = new Set();
  const cells = {}; // "state|symbol" -> { reachable, closure, target }

  for (let i = 0; i <= index && i < steps.length; i += 1) {
    const { kind, data } = steps[i];

    if (kind.startsWith("nfa.fragment.")) {
      nfaStates.add(data.start);
      nfaStates.add(data.accept);
      for (const state of data.result) nfaStates.add(state);
      for (const edge of data.edges ?? []) nfaEdges.add(edge);
    } else if (kind === "subset.state") {
      dfaStates[data.state] = data.nfa_states;
      if (data.result) accepting.add(data.state);
    } else if (kind === "subset.move") {
      const key = `${data.state}|${data.symbol}`;
      cells[key] = { reachable: data.result, closure: null, target: null };
    } else if (kind === "subset.closure") {
      if (data.symbol === undefined) {
        dfaStates[0] = data.result; // the start-state step
      } else {
        const key = `${data.state}|${data.symbol}`;
        cells[key] = {
          reachable: data.source,
          closure: data.result,
          target: data.target_state,
        };
        if (dfaStates[data.target_state] === undefined) {
          dfaStates[data.target_state] = data.result;
        }
      }
    }
  }

  return { nfaStates, nfaEdges, dfaStates, accepting, cells };
}

export default function RegexIndirectSteps({ step, index, steps, context }) {
  const acc = useMemo(() => accumulate(steps, index), [steps, index]);
  const nfa = useMemo(() => asGraph(context.nfa), [context.nfa]);

  const discoveredDfa = Object.keys(acc.dfaStates)
    .map(Number)
    .sort((a, b) => a - b);
  const alphabet = context.dfa?.alphabet ?? [];
  const inSubset = step.phase === "subset";

  // Only the moves and closures carry a working set worth spelling out.
  const working =
    step.kind === "subset.move"
      ? { move: step.data.result, closure: null, target: null }
      : step.kind === "subset.closure" && step.data.symbol !== undefined
        ? {
            move: step.data.source,
            closure: step.data.result,
            target: step.data.target_state,
          }
        : null;

  return (
    <div className="space-y-4">
      {working && (
        <div className="flex flex-wrap items-center gap-2 border border-graph bg-white px-4 py-3 font-mono text-sm">
          <span className="text-ink-faint">move</span>
          <span className="border border-blueprint bg-blueprint-light px-2 py-0.5 text-blueprint">
            {fmt(working.move)}
          </span>
          <span className="text-ink-faint">&rarr; &epsilon;-closure</span>
          <span
            className={`border px-2 py-0.5 ${
              working.closure
                ? "border-signal bg-signal-light text-ink"
                : "border-dashed border-graph text-ink-faint"
            }`}
          >
            {working.closure ? fmt(working.closure) : "not yet"}
          </span>
          {working.target !== null && (
            <>
              <span className="text-ink-faint">&rarr;</span>
              <span className="border border-circuit bg-circuit-light px-2 py-0.5 text-circuit">
                q{working.target}
              </span>
            </>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel title="Syntax tree" subtitle={context.pattern}>
          <AstTreeView ast={context.tree} highlight={step.highlight.nodes} />
        </Panel>

        <Panel
          title="Thompson NFA"
          subtitle={
            inSubset
              ? `${nfa?.num_states ?? 0} states`
              : `${acc.nfaStates.size} of ${nfa?.num_states ?? 0} states built`
          }
        >
          <DfaGraph
            dfa={nfa}
            highlight={{
              states: step.highlight.states,
              edges: step.highlight.edges,
              // Once subset construction starts the NFA is finished, so
              // everything stays lit and only the current subset stands out.
              discovered: inSubset ? undefined : [...acc.nfaStates],
            }}
          />
        </Panel>
      </div>

      {discoveredDfa.length > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Panel
            title="DFA under construction"
            subtitle={`${discoveredDfa.length} of ${context.dfa?.num_states ?? "?"} states found`}
          >
            <DfaGraph
              dfa={context.dfa}
              highlight={{
                // DFA indices come from the step's data; highlight.states
                // is reserved for NFA states on this page.
                states: [step.data.state, step.data.target_state].filter(
                  (s) => s !== undefined && s !== null,
                ),
                edges: step.highlight.edges,
                discovered: discoveredDfa,
              }}
            />
          </Panel>

          <Panel title="Subset table" variant="quiet" className="!p-0">
            <table className="w-full text-left font-mono text-sm">
              <thead>
                <tr className="border-b border-graph text-xs uppercase tracking-wide text-ink-faint">
                  <th className="px-4 py-2 font-medium">state</th>
                  <th className="px-4 py-2 font-medium">NFA states</th>
                  {alphabet.map((symbol) => (
                    <th key={symbol} className="px-3 py-2 font-medium">
                      {symbol}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {discoveredDfa.map((state) => (
                  <tr
                    key={state}
                    className={`border-b border-graph/60 last:border-b-0 ${
                      step.data.state === state ? "bg-signal-light" : ""
                    }`}
                  >
                    <td className="px-4 py-1.5 font-medium text-blueprint">
                      q{state}
                      {acc.accepting.has(state) && (
                        <span className="ml-1 text-circuit" title="accepting">
                          *
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-1.5 text-xs text-ink-faint">
                      {fmt(acc.dfaStates[state])}
                    </td>
                    {alphabet.map((symbol) => {
                      const cell = acc.cells[`${state}|${symbol}`];
                      return (
                        <td key={symbol} className="px-3 py-1.5 text-ink-soft">
                          {!cell ? "" : cell.target === null ? "—" : `q${cell.target}`}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>
      )}
    </div>
  );
}
