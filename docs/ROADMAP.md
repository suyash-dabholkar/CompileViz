# Roadmap

Each milestone is built on its own branch (see `CONTRIBUTING.md`), merged
into `main` via a pull request, and tagged once it lands. Check items off
as they're completed.

- [x] **Milestone 1 — Project scaffolding** (`feature/scaffolding`)
      FastAPI skeleton with `/health`, Vite + React app that calls it, CI
      running pytest on every PR. Tag `v0.1`.
- [ ] **Milestone 2 — Direct-method DFA engine** (`feature/direct-dfa`)
      Regex -> syntax tree -> nullable/firstpos/lastpos/followpos -> DFA.
- [ ] **Milestone 3 — Indirect method + benchmark** (`feature/indirect-dfa`)
      Thompson's construction -> subset construction, plus a benchmark
      comparing state count and build time against Milestone 2. Tag `v0.2`.
- [ ] **Milestone 4 — Regex playground** (`feature/regex-playground-api`,
      `feature/regex-playground-ui`)
      API endpoints for both DFA engines, React page with react-flow
      diagrams for each.
- [ ] **Milestone 5 — Grammar analysis tool** (`feature/grammar-analyzer`)
      FIRST/FOLLOW sets and LL(1) table generation. Tag `v0.3`.
- [ ] **Milestone 6 — DFA minimization** (`feature/dfa-minimization`)
      Partition refinement on top of the Milestone 2 DFA engine.
- [ ] **Milestone 7 — Lexer** (`feature/lexer`)
      Tokenizes toy-language source using the Milestone 2 DFA engine.
- [ ] **Milestone 8 — Parser and AST** (`feature/parser`)
      Built on the Milestone 5 grammar tool's LL(1) table.
- [ ] **Milestone 9 — Semantic analyzer** (`feature/semantic-analysis`)
      Scoped symbol table, type checking. Tag `v0.4`.
- [ ] **Milestone 10 — IR generator** (`feature/tac-generator`)
      AST -> three-address code.
- [ ] **Milestone 11 — Optimizer** (`feature/optimizer`)
      Constant folding, dead code elimination, CSE, before/after diffing.
- [ ] **Milestone 12 — Code generator** (`feature/codegen`)
      TAC -> stack-machine / assembly output, optional interpreter.
- [ ] **Milestone 13 — Full dashboard integration** (`feature/dashboard`)
      All six phases in one live, tabbed view with Monaco Editor as the
      code input. Tag `v0.5`.
- [ ] **Milestone 14 — Inline error highlighting** (`feature/error-highlighting`)
      Lexical, syntax, and semantic errors as inline Monaco markers.
- [ ] **Milestone 15 — Preset examples library** (`feature/presets`)
      Built-in regexes, grammars, and sample programs (valid + broken).
- [ ] **Milestone 16 — Deployment** (`feature/deployment`)
      Backend on Render/Railway, frontend on Vercel, connected end to end.
      Tag `v1.0`.
- [ ] **Milestone 17 — Polish and report prep**
      README screenshots, final docs, a full pass for rough edges before
      the demo.
