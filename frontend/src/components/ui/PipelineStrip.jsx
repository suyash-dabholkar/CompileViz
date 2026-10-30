// Sticky 7-phase status strip for the Compiler Pipeline page.
// Props: lexResult ({tokens, errors}) and analysis (the /analyze response) - both may be null.
const PHASES = [
  { id: "phase-lex", label: "Lex" },
  { id: "phase-parse", label: "Parse" },
  { id: "phase-semantic", label: "Semantic" },
  { id: "phase-tac", label: "TAC" },
  { id: "phase-opt", label: "Optimize" },
  { id: "phase-codegen", label: "Codegen" },
  { id: "phase-run", label: "Run" },
];

const STYLE = {
  pending: "border-graph bg-white text-ink-faint",
  ok: "border-circuit/50 bg-circuit-light text-circuit",
  error: "border-red-300 bg-red-50 text-red-700",
};
const DOT = {
  pending: "bg-graph",
  ok: "bg-circuit",
  error: "bg-red-500",
};

function states(lexResult, analysis) {
  const out = PHASES.map((p) => ({ ...p, state: "pending", note: "" }));
  if (lexResult) {
    const n = (lexResult.errors || []).length;
    out[0].state = n ? "error" : "ok";
    out[0].note = n ? `${n} error${n > 1 ? "s" : ""}` : `${(lexResult.tokens || []).length} tokens`;
  }
  if (analysis) {
    const pe = (analysis.parse_errors || []).length;
    out[1].state = pe ? "error" : "ok";
    out[1].note = pe ? `${pe} error${pe > 1 ? "s" : ""}` : "AST built";
    if (!pe) {
      const se = (analysis.semantic_errors || []).length;
      out[2].state = se ? "error" : "ok";
      out[2].note = se ? `${se} error${se > 1 ? "s" : ""}` : "types ok";
      if (!se) {
        const tac = analysis.original || [];
        out[3].state = "ok";
        out[3].note = `${tac.length} instr`;
        out[4].state = "ok";
        out[4].note = `-${analysis.instructions_removed ?? 0} instr`;
        out[5].state = "ok";
        out[5].note = `${(analysis.assembly || []).length} lines`;
        const rr = analysis.run_result;
        if (rr) {
          out[6].state = rr.runtime_error ? "error" : "ok";
          out[6].note = rr.runtime_error ? "runtime error" : `${rr.steps ?? 0} steps`;
        }
      }
    }
  }
  return out;
}

export function PipelineStrip({ lexResult, analysis }) {
  const items = states(lexResult, analysis);
  return (
    <nav
      aria-label="Compiler phases"
      className="sticky top-0 z-20 -mx-2 px-2 py-2 bg-paper/90 backdrop-blur border-b border-graph"
    >
      <ol className="flex gap-2 overflow-x-auto">
        {items.map((p, i) => (
          <li key={p.id} className="flex items-center gap-2 shrink-0">
            <a
              href={`#${p.id}`}
              className={`flex items-center gap-2 border px-3 py-1.5 text-xs font-mono transition-colors hover:brightness-95 ${STYLE[p.state]}`}
            >
              <span className={`h-2 w-2 rounded-full ${DOT[p.state]}`} />
              <span className="font-semibold">{p.label}</span>
              {p.note && <span className="opacity-70">{p.note}</span>}
            </a>
            {i < items.length - 1 && <span className="text-graph">→</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}
