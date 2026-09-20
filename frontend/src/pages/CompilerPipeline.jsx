import { useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import AstTreeView from "../components/AstTreeView";
import PresetPicker from "../components/PresetPicker";
import { Panel } from "../components/ui/Panel";
import { Button } from "../components/ui/Button";
import { PROGRAM_PRESETS } from "../presets/presets";
import { registerToyLanguage, registerToyTheme } from "../editor/toyLanguage";
import { buildErrorMarkers, MARKER_OWNER } from "../editor/errorMarkers";
import { runProgram, tokenizeSource } from "../api/compilerApi";
import { extractErrorMessage } from "../api/client";

const DEFAULT_SOURCE = `int x;
x = 2 + 3 * 4;
if (x > 10) {
    x = x - 1;
} else {
    x = x + 1;
}
// a comment
while (x > 0) {
    x = x - 1;
}
print(x);`;

function ErrorList({ errors }) {
  if (errors.length === 0) return null;
  return (
    <div className="mb-3 space-y-1">
      {errors.map((err, i) => (
        <div key={i} className="border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-700">
          Line {err.line}, column {err.column}: {err.message}
        </div>
      ))}
    </div>
  );
}

function CodeListing({ instructions, emptyLabel = "(no instructions)" }) {
  return (
    <pre className="font-mono text-sm text-ink leading-6 overflow-x-auto">
      {instructions.length === 0
        ? emptyLabel
        : instructions
            .map((instr) => (instr.op === "LABEL" ? instr.text : `    ${instr.text}`))
            .join("\n")}
    </pre>
  );
}

// This page grows one phase at a time: Milestone 7 added the lexer
// section, Milestone 8 added syntax analysis (the AST), Milestone 9
// added semantic analysis (the symbol table and type checking),
// Milestone 10 added intermediate code (three-address code),
// Milestone 11 added optimization, Milestone 12 added code generation
// and actually running the program, Milestone 13 swapped the plain
// textarea for the Monaco editor (with real syntax highlighting for
// the toy language, see ../editor/toyLanguage.js), Milestone 14 added
// inline error highlighting on top of that editor (see
// ../editor/errorMarkers.js), and Milestone 15 adds the preset
// programs picker above the editor (see ../presets/presets.js), so a
// demo never needs to type a single character. /api/compiler/codegen
// returns everything every earlier endpoint did plus the generated
// assembly and the run result, so this page only needs that one call
// (plus /tokenize for the raw token table and accurate underline
// widths). All six PRD phases are live in this one tab now, all
// reading from the same source editor.
export default function CompilerPipeline() {
  const [source, setSource] = useState(DEFAULT_SOURCE);
  const [lexResult, setLexResult] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const editorRef = useRef(null);
  const monacoRef = useRef(null);

  function handleEditorMount(editor, monaco) {
    editorRef.current = editor;
    monacoRef.current = monaco;
  }

  function clearMarkers() {
    const monaco = monacoRef.current;
    const editor = editorRef.current;
    if (!monaco || !editor) return;
    const model = editor.getModel();
    if (model) monaco.editor.setModelMarkers(model, MARKER_OWNER, []);
  }

  function handleSourceChange(value) {
    setSource(value ?? "");
    // The squiggles reflect the LAST compile, not the current text, so
    // clear them immediately on edit rather than leaving stale
    // underlines pointing at positions that no longer mean what they
    // did. Fresh markers reappear after the next Compile.
    clearMarkers();
  }

  function handlePresetSelect(preset) {
    setSource(preset.source);
    clearMarkers();
  }

  async function handleCompile(e) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const [lex, analyzed] = await Promise.all([
        tokenizeSource(source),
        runProgram(source),
      ]);
      setLexResult(lex);
      setAnalysis(analyzed);

      const monaco = monacoRef.current;
      const editor = editorRef.current;
      if (monaco && editor) {
        const model = editor.getModel();
        if (model) {
          const markers = buildErrorMarkers(monaco, {
            lexErrors: lex.errors,
            parseErrors: analyzed.parse_errors,
            semanticErrors: analyzed.semantic_errors,
            tokens: lex.tokens,
          });
          monaco.editor.setModelMarkers(model, MARKER_OWNER, markers);
        }
      }
    } catch (err) {
      setError(extractErrorMessage(err));
      setLexResult(null);
      setAnalysis(null);
      clearMarkers();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Compiler Pipeline</h1>
        <p className="text-ink-soft text-sm mt-1 max-w-2xl">
          Write toy-language source code and watch it move through
          every phase, lexing, parsing, semantic analysis, intermediate
          code, optimization, and code generation, then see the program
          actually run.
        </p>
      </header>

      <PresetPicker
        label="Preset programs (valid and intentionally broken)"
        presets={PROGRAM_PRESETS}
        onSelect={handlePresetSelect}
      />

      <div className="space-y-2">
        <div className="border border-ink/25 overflow-hidden">
          <Editor
            height="260px"
            language="toylang"
            value={source}
            onChange={handleSourceChange}
            beforeMount={(monaco) => {
              registerToyLanguage(monaco);
              registerToyTheme(monaco);
            }}
            onMount={handleEditorMount}
            theme="compileviz"
            options={{
              fontSize: 14,
              fontFamily: "'JetBrains Mono', monospace",
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              automaticLayout: true,
              wordWrap: "on",
            }}
          />
        </div>
        <Button onClick={handleCompile} disabled={loading || !source.trim()}>
          {loading ? "Compiling…" : "Compile"}
        </Button>
      </div>

      {error && (
        <div className="border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {lexResult && (
        <Panel
          title="Lexical analysis"
          subtitle={`${lexResult.tokens.length} tokens${
            lexResult.errors.length > 0 ? `, ${lexResult.errors.length} error(s)` : ""
          }`}
        >
          <ErrorList errors={lexResult.errors} />
          <div className="overflow-x-auto max-h-72 -m-4 mt-0">
            <table className="min-w-full text-sm">
              <thead>
                <tr>
                  <th className="px-4 py-2.5 text-left font-medium text-ink-soft border-b border-graph sticky top-0 bg-white">
                    Type
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-ink-soft border-b border-graph sticky top-0 bg-white">
                    Value
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-ink-soft border-b border-graph sticky top-0 bg-white">
                    Line
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-ink-soft border-b border-graph sticky top-0 bg-white">
                    Column
                  </th>
                </tr>
              </thead>
              <tbody>
                {lexResult.tokens.map((token, i) => (
                  <tr key={i} className="odd:bg-white even:bg-paper/60">
                    <td className="px-4 py-1.5 font-mono text-blueprint border-b border-graph/60">
                      {token.type}
                    </td>
                    <td className="px-4 py-1.5 font-mono text-ink border-b border-graph/60">
                      {token.value}
                    </td>
                    <td className="px-4 py-1.5 text-ink-faint border-b border-graph/60">{token.line}</td>
                    <td className="px-4 py-1.5 text-ink-faint border-b border-graph/60">{token.column}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {analysis && (
        <Panel
          title="Syntax analysis"
          subtitle={analysis.parse_errors.length > 0 ? `${analysis.parse_errors.length} error(s)` : "no syntax errors"}
        >
          <ErrorList errors={analysis.parse_errors} />
          <AstTreeView ast={analysis.ast} />
        </Panel>
      )}

      {analysis && (
        <Panel
          title="Semantic analysis"
          subtitle={
            analysis.semantic_errors.length > 0 ? `${analysis.semantic_errors.length} error(s)` : "no semantic errors"
          }
        >
          <ErrorList errors={analysis.semantic_errors} />

          <p className="text-xs font-medium text-ink-faint mb-1">Symbol table</p>
          <div className="overflow-x-auto border border-graph">
            <table className="min-w-full text-sm">
              <thead>
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-ink-soft border-b border-graph bg-paper/60">
                    Name
                  </th>
                  <th className="px-4 py-2 text-left font-medium text-ink-soft border-b border-graph bg-paper/60">
                    Type
                  </th>
                  <th className="px-4 py-2 text-left font-medium text-ink-soft border-b border-graph bg-paper/60">
                    Scope depth
                  </th>
                  <th className="px-4 py-2 text-left font-medium text-ink-soft border-b border-graph bg-paper/60">
                    Declared at
                  </th>
                </tr>
              </thead>
              <tbody>
                {analysis.symbols.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-2 text-ink-faint text-center">
                      No variables declared
                    </td>
                  </tr>
                )}
                {analysis.symbols.map((sym, i) => (
                  <tr key={i} className="odd:bg-white even:bg-paper/60">
                    <td className="px-4 py-1.5 font-mono text-ink border-b border-graph/60">{sym.name}</td>
                    <td className="px-4 py-1.5 font-mono text-blueprint border-b border-graph/60">{sym.type}</td>
                    <td className="px-4 py-1.5 text-ink-faint border-b border-graph/60">{sym.scope_depth}</td>
                    <td className="px-4 py-1.5 text-ink-faint border-b border-graph/60">
                      {sym.line}:{sym.column}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {analysis && (
        <Panel
          title="Intermediate code (three-address code)"
          subtitle={`${analysis.original.length} instruction${analysis.original.length === 1 ? "" : "s"}`}
        >
          <div className="max-h-96 overflow-y-auto">
            <CodeListing instructions={analysis.original} />
          </div>
        </Panel>
      )}

      {analysis && (
        <div>
          <h2 className="text-sm font-medium text-ink-soft mb-2">
            Optimization
            <span className="ml-2 text-xs text-ink-faint font-normal">
              constant folding &amp; propagation &rarr; common subexpression elimination &rarr; dead code
              elimination
              {analysis.instructions_removed > 0
                ? ` — ${analysis.instructions_removed} instruction(s) removed`
                : " — nothing to remove here"}
            </span>
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Panel title="Before optimization">
              <div className="max-h-96 overflow-y-auto">
                <CodeListing instructions={analysis.original} />
              </div>
            </Panel>
            <Panel title="After optimization" className="!border-circuit/40">
              <div className="max-h-96 overflow-y-auto">
                <CodeListing instructions={analysis.after_dce} emptyLabel="(fully eliminated)" />
              </div>
            </Panel>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-3 text-xs text-ink-faint font-mono">
            <div>folding: {analysis.after_constant_folding.length} instr.</div>
            <div>CSE: {analysis.after_cse.length} instr.</div>
            <div>DCE: {analysis.after_dce.length} instr.</div>
          </div>
        </div>
      )}

      {analysis && (
        <Panel
          title="Code generation (stack-machine assembly)"
          subtitle={`${analysis.assembly.length} instruction${analysis.assembly.length === 1 ? "" : "s"}`}
        >
          <div className="max-h-96 overflow-y-auto">
            <CodeListing instructions={analysis.assembly} />
          </div>
        </Panel>
      )}

      {analysis && (
        <Panel title="Program output">
          <div className="bg-ink -m-4 p-4 font-mono text-sm min-h-[3rem]">
            {analysis.run_result.output.length === 0 && !analysis.run_result.runtime_error && (
              <span className="text-paper/40">(no output)</span>
            )}
            {analysis.run_result.output.map((line, i) => (
              <div key={i} className="text-circuit">
                {line}
              </div>
            ))}
            {analysis.run_result.runtime_error && (
              <div className="text-signal mt-1">Runtime error: {analysis.run_result.runtime_error}</div>
            )}
          </div>

          {Object.keys(analysis.run_result.variables).length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-medium text-ink-faint mb-1.5">Final variable values</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(analysis.run_result.variables).map(([name, value]) => (
                  <span key={name} className="bg-paper px-2 py-1 font-mono text-xs text-ink border border-graph">
                    {name} = {value}
                  </span>
                ))}
              </div>
            </div>
          )}

          <p className="mt-3 text-xs text-ink-faint font-mono">
            {analysis.run_result.steps} instruction{analysis.run_result.steps === 1 ? "" : "s"} executed
          </p>
        </Panel>
      )}
    </div>
  );
}
