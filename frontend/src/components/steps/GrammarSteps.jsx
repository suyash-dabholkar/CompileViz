import { useMemo } from "react";
import Ll1TableView from "../Ll1TableView";
import { Panel } from "../ui/Panel";

/**
 * Draws one step of the grammar analysis: the FIRST fixed point, then
 * the FOLLOW fixed point, then the LL(1) table being filled.
 *
 * The sets are folded from the steps rather than read from the final
 * answer in `context`, so a set only shows what has actually been
 * derived so far. Watching FIRST(E) stay empty for two whole sweeps
 * because it is waiting on FIRST(T) is the point of a fixed point, and
 * the finished table cannot show it.
 */

const fmt = (values) => (values?.length ? `{${values.join(", ")}}` : "{}");

function accumulate(steps, index, context) {
  const nonTerminals = context.non_terminals ?? [];
  const first = Object.fromEntries(nonTerminals.map((nt) => [nt, []]));
  const follow = Object.fromEntries(nonTerminals.map((nt) => [nt, []]));
  const rows = {}; // non-terminal -> { terminal: [productions] }
  let conflicts = 0;

  for (let i = 0; i <= index && i < steps.length; i += 1) {
    const { kind, data } = steps[i];

    if (kind === "first.production") {
      first[data.non_terminal] = data.current;
    } else if (kind === "follow.init") {
      follow[data.non_terminal] = data.result;
    } else if (kind === "follow.production") {
      follow[data.non_terminal] = data.current;
    } else if (kind === "ll1.production") {
      const row = (rows[data.non_terminal] ??= {});
      for (const terminal of data.result) {
        (row[terminal] ??= []).push(data.production);
      }
    } else if (kind === "ll1.conflict") {
      conflicts += 1;
    }
  }

  return { first, follow, rows, conflicts };
}

export default function GrammarSteps({ step, index, steps, context }) {
  const acc = useMemo(
    () => accumulate(steps, index, context),
    [steps, index, context],
  );

  const nonTerminals = context.non_terminals ?? [];
  const active = step.highlight.rows;
  const inTable = step.kind.startsWith("ll1.");

  // Only the cells derived so far, in the shape Ll1TableView already
  // expects, so the finished table component doubles as the live one.
  const partialTable = useMemo(
    () =>
      context.ll1_table && {
        ...context.ll1_table,
        table: acc.rows,
        conflicts: (context.ll1_table.conflicts ?? []).slice(0, acc.conflicts),
        is_ll1: acc.conflicts === 0,
      },
    [context.ll1_table, acc.rows, acc.conflicts],
  );

  return (
    <div className="space-y-4">
      <Panel title="FIRST and FOLLOW so far" variant="quiet" className="!p-0">
        <table className="w-full text-left font-mono text-sm">
          <thead>
            <tr className="border-b border-graph text-xs uppercase tracking-wide text-ink-faint">
              <th className="px-4 py-2 font-medium">non-terminal</th>
              <th className="px-4 py-2 font-medium">FIRST</th>
              <th className="px-4 py-2 font-medium">FOLLOW</th>
            </tr>
          </thead>
          <tbody>
            {nonTerminals.map((nt) => (
              <tr
                key={nt}
                className={`border-b border-graph/60 last:border-b-0 ${
                  active.includes(nt) ? "bg-signal-light" : ""
                }`}
              >
                <td className="px-4 py-1.5 font-medium text-blueprint">{nt}</td>
                <td className="px-4 py-1.5 text-ink-soft">
                  {acc.first[nt]?.length ? fmt(acc.first[nt]) : "—"}
                </td>
                <td className="px-4 py-1.5 text-ink-soft">
                  {acc.follow[nt]?.length ? fmt(acc.follow[nt]) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      {inTable && partialTable && (
        <Panel
          title="LL(1) parsing table"
          subtitle={
            acc.conflicts > 0
              ? `${acc.conflicts} conflict(s) so far`
              : "no conflicts so far"
          }
          className="!p-0"
        >
          <Ll1TableView table={partialTable} />
        </Panel>
      )}

      {step.data.production && (
        <Panel title="Production in hand" variant="quiet">
          <p className="font-mono text-sm text-ink">
            <span className="text-blueprint">{step.data.non_terminal}</span>
            <span className="mx-2 text-ink-faint">&rarr;</span>
            {step.data.production}
          </p>
        </Panel>
      )}
    </div>
  );
}
