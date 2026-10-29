# CompileViz UI extras - integration (about 10 min)

Copy `src/components/ui/WakeUpBanner.jsx`, `src/components/ui/PipelineStrip.jsx`, `src/polish.css` into the same paths in `frontend/`.

## 1. polish.css  (main.jsx)
Add after the `index.css` import:
    import "./polish.css";

## 2. Wake-up banner (App.jsx)
    import { WakeUpBanner } from "./components/ui/WakeUpBanner";
Render `<WakeUpBanner status={backendStatus} />` directly ABOVE `<header>`.
(Use whatever variable holds your health status; values: "ok" | "unreachable" | other = checking.)
Make the health check patient: change `checkHealth(2)` / 1500 ms to `checkHealth(20)` / 3000 ms
so it keeps retrying for about a minute while Render wakes up.

## 3. Pipeline strip (CompilerPipeline.jsx)
    import { PipelineStrip } from "../components/ui/PipelineStrip";
Put `<PipelineStrip lexResult={lexResult} analysis={analysis} />` at the top of the page content
(rename props to your state variables). Add ids to each phase panel wrapper:
`id="phase-lex"`, `phase-parse`, `phase-semantic`, `phase-tac`, `phase-opt`, `phase-codegen`, `phase-run`
(optionally add className="phase-section" for the fade-in).
Field names used from analysis: parse_errors, semantic_errors, original, instructions_removed,
assembly, run_result.{runtime_error,steps}. If your friend renamed any, adjust `states()` in PipelineStrip.jsx.

## 4. Ctrl+Enter to compile (CompilerPipeline.jsx)
    const runRef = useRef(null);
    runRef.current = handleCompile;            // your existing compile handler
    // in Monaco's onMount (editor, monaco):
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => runRef.current?.());
Add a small hint next to the Compile button: "Ctrl+Enter".

Tailwind tokens used (already in your config): signal, signal-dark, signal-light, circuit, circuit-light, graph, paper, ink-faint.
Test on a branch, click all four tabs, then merge.
