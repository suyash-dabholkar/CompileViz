import { useMemo } from "react";
import AstTreeView from "../AstTreeView";
import DfaGraph from "../DfaGraph";
import { Panel } from "../ui/Panel";

/**
 * Draws one step of the direct (followpos) DFA construction.
 *
 * Everything on screen is derived by folding the steps up to the current
 * index, so nothing is revealed before the step that computes it: the
 * leaves get their position numbers one at a time, the firstpos/lastpos
 * badges fill in bottom-up, the followpos column fills per rule, and the
 * transition table fills one cell at a time.
 *
 * The DFA graph always renders the finished automaton and reveals it with
 * `highlight.discovered` rather than growing node by node - a graph whose
 * node count changes would remount react-flow and refit the camera on
 * every keypress (see graphIdentity in DfaGraph.jsx).
 */

const fmt = (values) => (values?.length ? `{${values.join(", ")}}` : "{}");

/** Replay the trace up to `index` into the tables the UI draws. */
function accumulate(steps, index) {
  const positions = {}; // position -> symbol
  const attrs = {}; // node id -> { nullable, firstpos, lastpos }
  const followpos = {}; // position -> number[]
  const states = {}; // DFA state index -> positions
  const accepting = new Set();
  const moves = {}; // "state|symbol" -> target index, or null for a blank
  let augmented = false;

  for (let i = 0; i <= index && i < steps.length; i += 1) {
    const { kind, data } = steps[i];

    if (kind === "regex.augment") {
      augmented = true;
    } else if (kind === "regex.position") {
      positions[data.result] = data.symbol;
    } else if (kind.startsWith("regex.attrs.")) {
      attrs[data.node] = {
        nullable: data.nullable,
        firstpos: data.firstpos,
        lastpos: data.lastpos,
      };
    } else if (kind.startsWith("regex.followpos.")) {
      for (const position of data.result) {
        const merged = new Set([...(followpos[position] ?? []), ...data.gained]);
        followpos[position] = [...merged].sort((a, b) => a - b);
      }
    } else if (kind === "subset.start") {
      states[0] = data.result;
    } else if (kind === "subset.state") {
      states[data.state] = data.positions;
      if (data.result) accepting.add(data.state);
    } else if (kind === "subset.move") {
      moves[`${data.state}|${data.symbol}`] = data.target_state;
      if (data.target_state !== null && states[data.target_state] === undefined) {
        states[data.target_state] = data.result;
      }
    }
  }

  return { positions, attrs, followpos, states, accepting, moves, augmented };
}

/** Hide what the trace has not reached yet. */
function maskTree(tree, acc) {
  if (!tree) return null;

  const visit = (node) => {
    const out = { ...node };
    if (node.kind === "Leaf" && !(node.position in acc.positions)) {
      out.position = null;
    }
    for (const key of ["left", "right", "child"]) {
      if (out[key]) out[key] = visit(out[key]);
    }
    return out;
  };

  // The augmented root is Concat(original, #), so before the augment
  // step the original pattern's tree is its left child.
  return visit(acc.augmented ? tree : (tree.left ?? tree));
}

export default function RegexDirectSteps({ step, index, steps, context }) {
  const acc = useMemo(() => accumulate(steps, index), [steps, index]);
  const tree = useMemo(() => maskTree(context.tree, acc), [context.tree, acc]);

  const discovered = Object.keys(acc.states)
    .map(Number)
    .sort((a, b) => a - b);
  const assigned = Object.keys(acc.positions).map(Number).sort((a, b) => a - b);
  const alphabet = context.dfa?.alphabet ?? [];
  const hasMoves = Object.keys(acc.moves).length > 0;

  const annotate = (node) => {
    const node_attrs = acc.attrs[node.id];
    const parts = [];
    if (node_attrs) {
      parts.push(`first=${fmt(node_attrs.firstpos)}`);
      parts.push(`last=${fmt(node_attrs.lastpos)}`);
      if (node_attrs.nullable) parts.push("nullable");
    }
    const follows = node.kind === "Leaf" ? acc.followpos[node.position] : null;
    if (follows?.length) parts.push(`follow=${fmt(follows)}`);
    return parts.length ? parts.join("  ") : null;
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel title="Syntax tree" subtitle={context.pattern}>
          <AstTreeView ast={tree} highlight={step.highlight.nodes} annotate={annotate} />
        </Panel>

        <Panel title="Positions and followpos" variant="quiet" className="!p-0">
          {assigned.length === 0 ? (
            <p className="p-4 text-sm text-ink-faint">
              No positions assigned yet. The leaves get numbered left to right.
            </p>
          ) : (
            <table className="w-full text-left font-mono text-sm">
              <thead>
                <tr className="border-b border-graph text-xs uppercase tracking-wide text-ink-faint">
                  <th className="px-4 py-2 font-medium">pos</th>
                  <th className="px-4 py-2 font-medium">symbol</th>
                  <th className="px-4 py-2 font-medium">followpos</th>
                </tr>
              </thead>
              <tbody>
                {assigned.map((position) => {
                  const active = step.highlight.positions.includes(position);
                  return (
                    <tr
                      key={position}
                      className={`border-b border-graph/60 last:border-b-0 ${
                        active ? "bg-signal-light" : ""
                      }`}
                    >
                      <td className="px-4 py-1.5 text-ink-soft">{position}</td>
                      <td className="px-4 py-1.5 font-medium text-blueprint">
                        {acc.positions[position]}
                      </td>
                      <td className="px-4 py-1.5 text-ink-soft">
                        {acc.followpos[position] ? fmt(acc.followpos[position]) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Panel>
      </div>

      {discovered.length > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Panel
            title="DFA under construction"
            subtitle={`${discovered.length} of ${context.dfa?.num_states ?? "?"} states found`}
          >
            <DfaGraph
              dfa={context.dfa}
              highlight={{
                states: step.highlight.states,
                edges: step.highlight.edges,
                discovered,
              }}
            />
          </Panel>

          <Panel title="Transition table" variant="quiet" className="!p-0">
            {!hasMoves ? (
              <p className="p-4 text-sm text-ink-faint">
                The start state is known. Next, work out where it goes on each
                input symbol.
              </p>
            ) : (
              <table className="w-full text-left font-mono text-sm">
                <thead>
                  <tr className="border-b border-graph text-xs uppercase tracking-wide text-ink-faint">
                    <th className="px-4 py-2 font-medium">state</th>
                    <th className="px-4 py-2 font-medium">positions</th>
                    {alphabet.map((symbol) => (
                      <th key={symbol} className="px-3 py-2 font-medium">
                        {symbol}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {discovered.map((state) => (
                      <tr
                        key={state}
                        className={`border-b border-graph/60 last:border-b-0 ${
                          step.highlight.states.includes(state) ? "bg-signal-light" : ""
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
                        <td className="px-4 py-1.5 text-ink-faint">
                          {fmt(acc.states[state])}
                        </td>
                        {alphabet.map((symbol) => {
                          const key = `${state}|${symbol}`;
                          const target = acc.moves[key];
                          return (
                            <td key={symbol} className="px-3 py-1.5 text-ink-soft">
                              {!(key in acc.moves)
                                ? ""
                                : target === null
                                  ? "—"
                                  : `q${target}`}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                </tbody>
              </table>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}
