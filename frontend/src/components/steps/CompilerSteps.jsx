import { useMemo } from "react";
import { Panel } from "../ui/Panel";

/**
 * Draws one step of the compiler pipeline. Two phases are instrumented
 * so far and they want completely different pictures, so this dispatches
 * on the step's phase rather than trying to find one layout for both.
 *
 *  lex  the source with the current characters lit, which patterns are
 *       competing, and the winning DFA's walk character by character
 *  run  the assembly listing with the program counter, the operand
 *       stack, the variables and anything printed so far
 */

function SourceView({ source, chars }) {
  const lit = new Set(chars);
  return (
    <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-sm leading-relaxed text-ink-soft">
      {[...source].map((character, i) => (
        <span
          key={i}
          className={lit.has(i) ? "bg-signal text-ink" : undefined}
        >
          {character}
        </span>
      ))}
    </pre>
  );
}

function accumulate(steps, index) {
  const tokens = [];
  const output = [];
  let stack = [];
  let variables = {};
  let pc = null;

  for (let i = 0; i <= index && i < steps.length; i += 1) {
    const { kind, data } = steps[i];
    if (kind === "lex.token") {
      tokens.push({
        type: data.token_type,
        value: data.result,
        skipped: data.skipped,
        reclassified: data.reclassified,
      });
    } else if (kind === "vm.step" || kind === "vm.jump" || kind === "vm.halt") {
      stack = data.stack ?? stack;
      variables = data.variables ?? variables;
      if (data.pc !== undefined) pc = data.next_pc;
      for (const line of data.printed ?? []) output.push(line);
    }
  }

  return { tokens, output, stack, variables, pc };
}

export default function CompilerSteps({ step, index, steps, context }) {
  const acc = useMemo(() => accumulate(steps, index), [steps, index]);
  const isLex = step.kind.startsWith("lex.");

  return (
    <div className="space-y-4">
      {isLex ? (
        <LexView step={step} acc={acc} context={context} />
      ) : (
        <RunView step={step} acc={acc} context={context} />
      )}
    </div>
  );
}

function LexView({ step, acc, context }) {
  const candidates = step.data.candidates;

  return (
    <>
      <Panel title="Source" subtitle={`offset ${step.data.offset ?? "-"}`}>
        <SourceView source={context.source ?? ""} chars={step.highlight.chars} />
      </Panel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {candidates ? (
          <Panel
            title="Patterns competing here"
            subtitle={`${candidates.length} match`}
            variant="quiet"
            className="!p-0"
          >
            <table className="w-full text-left font-mono text-sm">
              <thead>
                <tr className="border-b border-graph text-xs uppercase tracking-wide text-ink-faint">
                  <th className="px-4 py-2 font-medium">pattern</th>
                  <th className="px-4 py-2 font-medium">chars matched</th>
                </tr>
              </thead>
              <tbody>
                {[...candidates]
                  .sort((a, b) => b.length - a.length)
                  .map((candidate) => (
                    <tr
                      key={candidate.type}
                      className={`border-b border-graph/60 last:border-b-0 ${
                        candidate.type === step.data.result ? "bg-signal-light" : ""
                      }`}
                    >
                      <td className="px-4 py-1.5 text-blueprint">{candidate.type}</td>
                      <td className="px-4 py-1.5 text-ink-soft">{candidate.length}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </Panel>
        ) : (
          <Panel title="DFA walk" variant="quiet">
            {step.kind === "lex.scan" ? (
              <div className="space-y-2 font-mono text-sm">
                <div className="flex items-center gap-2">
                  <span className="border border-graph bg-white px-2 py-0.5 text-ink-soft">
                    state {step.data.state_before}
                  </span>
                  <span className="text-ink-faint">
                    &mdash;{JSON.stringify(step.data.char)}&rarr;
                  </span>
                  {step.data.state_after === null ? (
                    <span className="border border-red-300 bg-red-50 px-2 py-0.5 text-red-700">
                      no transition
                    </span>
                  ) : (
                    <span
                      className={`border px-2 py-0.5 ${
                        step.data.accepting
                          ? "border-circuit bg-circuit-light text-circuit"
                          : "border-graph bg-white text-ink-soft"
                      }`}
                    >
                      state {step.data.state_after}
                      {step.data.accepting ? " (accepting)" : ""}
                    </span>
                  )}
                </div>
                <p className="text-xs text-ink-faint">
                  longest match so far: {step.data.best_length} character(s)
                </p>
              </div>
            ) : (
              <p className="text-sm text-ink-faint">
                {step.kind === "lex.error"
                  ? "No pattern accepted this character."
                  : "Token complete."}
              </p>
            )}
          </Panel>
        )}

        <Panel
          title="Tokens so far"
          subtitle={`${acc.tokens.filter((t) => !t.skipped).length} kept`}
          variant="quiet"
        >
          {acc.tokens.length === 0 ? (
            <p className="text-sm text-ink-faint">Nothing scanned yet.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {acc.tokens.map((token, i) => (
                <span
                  key={i}
                  title={token.type}
                  className={`border px-2 py-0.5 font-mono text-xs ${
                    token.skipped
                      ? "border-dashed border-graph text-ink-faint"
                      : token.reclassified
                        ? "border-circuit bg-circuit-light text-circuit"
                        : "border-graph bg-white text-ink-soft"
                  }`}
                >
                  {JSON.stringify(token.value)}
                </span>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}

function RunView({ step, acc, context }) {
  const assembly = context.assembly ?? [];
  const currentPc = step.data.pc;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Panel title="Stack machine" subtitle={`pc ${currentPc ?? "-"}`} className="!p-0">
        <ol className="max-h-80 overflow-y-auto font-mono text-sm">
          {assembly.map((instr, i) => (
            <li
              key={i}
              className={`flex gap-3 px-4 py-1 ${
                i === currentPc ? "bg-signal-light" : ""
              }`}
            >
              <span className="w-8 shrink-0 text-right text-ink-faint">
                {i === currentPc ? "▸" : ""} {i}
              </span>
              <span className={i === currentPc ? "text-ink" : "text-ink-soft"}>
                {instr.text}
              </span>
            </li>
          ))}
        </ol>
      </Panel>

      <div className="space-y-4">
        <Panel title="Operand stack" variant="quiet">
          {acc.stack.length === 0 ? (
            <p className="font-mono text-sm text-ink-faint">empty</p>
          ) : (
            // Top of stack first: that is the end every instruction
            // actually touches.
            <div className="flex flex-col-reverse gap-1">
              {acc.stack.map((value, i) => (
                <div
                  key={i}
                  className={`border px-2.5 py-1 font-mono text-sm ${
                    i === acc.stack.length - 1
                      ? "border-signal bg-signal-light text-ink"
                      : "border-graph bg-white text-ink-soft"
                  }`}
                >
                  {value}
                  {i === acc.stack.length - 1 && (
                    <span className="ml-2 text-xs text-ink-faint">top</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Variables" variant="quiet">
          {Object.keys(acc.variables).length === 0 ? (
            <p className="font-mono text-sm text-ink-faint">none assigned</p>
          ) : (
            <table className="w-full text-left font-mono text-sm">
              <tbody>
                {Object.entries(acc.variables).map(([name, value]) => (
                  <tr key={name} className="border-b border-graph/60 last:border-b-0">
                    <td className="py-1 pr-4 text-blueprint">{name}</td>
                    <td className="py-1 text-ink-soft">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>

        <Panel title="Output" variant="quiet">
          {acc.output.length === 0 ? (
            <p className="font-mono text-sm text-ink-faint">nothing printed yet</p>
          ) : (
            <pre className="font-mono text-sm text-ink-soft">
              {acc.output.join("\n")}
            </pre>
          )}
        </Panel>
      </div>
    </div>
  );
}
