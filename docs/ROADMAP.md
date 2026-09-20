# Roadmap

Every milestone is built on its own branch (see `CONTRIBUTING.md`),
merged into `main` via a pull request, and tagged once it lands.

- [x] **Milestone 1 — Project scaffolding**
      FastAPI skeleton with `/health`, Vite + React app that calls it,
      CI running pytest on every PR.
- [x] **Milestone 2 — Direct-method DFA engine**
      Regex -> syntax tree -> nullable/firstpos/lastpos/followpos -> DFA.
- [x] **Milestone 3 — Indirect method + benchmark**
      Thompson's construction -> subset construction, plus a benchmark
      comparing state count and build time against Milestone 2.
- [x] **Milestone 4 — Regex playground**
      API endpoints for both DFA engines, React page with react-flow
      diagrams for each.
- [x] **Milestone 5 — Grammar analysis tool**
      FIRST/FOLLOW sets and LL(1) table generation.
- [x] **Milestone 6 — DFA minimization**
      Partition refinement on top of the Milestone 2 DFA engine.
- [x] **Milestone 7 — Lexer**
      Tokenizes toy-language source using the Milestone 2 DFA engine.
- [x] **Milestone 8 — Parser and AST**
      Built on the Milestone 5 grammar tool's LL(1) table.
- [x] **Milestone 9 — Semantic analyzer**
      Scoped symbol table, type checking.
- [x] **Milestone 10 — IR generator**
      AST -> three-address code.
- [x] **Milestone 11 — Optimizer**
      Constant folding, dead code elimination, CSE, before/after diffing.
- [x] **Milestone 12 — Code generator**
      TAC -> stack-machine / assembly output, plus an interpreter that
      actually runs it.
- [x] **Milestone 13 — Full dashboard integration**
      All six phases in one live, tabbed view with the Monaco editor
      (and real toy-language syntax highlighting) as the code input.
- [x] **Milestone 14 — Inline error highlighting**
      Lexical, syntax, and semantic errors as inline Monaco markers.
- [x] **Milestone 15 — Preset examples library**
      Built-in regexes, grammars, and sample programs (valid + broken).
- [x] **Milestone 16 — Deployment**
      Backend on Render, frontend on Vercel, connected end to end.
      Live at https://compile-viz.vercel.app
- [x] **Milestone 17 — Polish and report prep**
      README screenshots, final docs, a full pass for rough edges
      before the demo.

## Project complete

Every milestone above is done. The full write-up for the course
report lives in `Visual_Compiler_PRD.pdf` / the generated report
document, this file is the build history, not the report itself.
