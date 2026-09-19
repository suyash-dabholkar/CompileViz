import { useState } from "react";
import AstTreeView from "../components/AstTreeView";
import { optimizeSource, tokenizeSource } from "../api/compilerApi";
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

// This page grows one phase at a time: Milestone 7 added the lexer
// section, Milestone 8 added syntax analysis (the AST), Milestone 9
// added semantic analysis (the symbol table and type checking),
// Milestone 10 added intermediate code (three-address code), and
// Milestone 11 adds optimization below that. /api/compiler/optimize
// returns everything /api/compiler/tac does plus every optimization
// pass's before/after TAC, so this page only needs that one call
// (plus /tokenize for the raw token table). Milestone 12 and beyond
// each add their own section here, all reading from the same source
// textarea, matching the PRD's tabbed dashboard where every phase
// updates live from one piece of source code.
export default function CompilerPipeline() {
  const [source, setSource] = useState(DEFAULT_SOURCE);
  const [lexResult, setLexResult] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleCompile(e) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const [lex, analyzed] = await Promise.all([
        tokenizeSource(source),
        optimizeSource(source),
      ]);
      setLexResult(lex);
      setAnalysis(analyzed);
    } catch (err) {
      setError(extractErrorMessage(err));
      setLexResult(null);
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-800">Compiler Pipeline</h1>
        <p className="text-slate-600 text-sm mt-1">
          Write toy-language source code and watch it move through each
          phase. Lexical, syntax, semantic, intermediate-code, and
          optimization passes are all live now, more phases (code
          generation and beyond) get added here as they're built.
        </p>
      </header>

      <form onSubmit={handleCompile} className="space-y-2">
        <textarea
          value={source}
          onChange={(e) => setSource(e.target.value)}
          rows={10}
          spellCheck={false}
          className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          type="submit"
          disabled={loading || !source.trim()}
          className="rounded-md bg-blue-700 px-4 py-2 text-white font-medium disabled:opacity-50"
        >
          {loading ? "Compiling..." : "Compile"}
        </button>
      </form>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {lexResult && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-2">
            Lexical analysis
            <span className="ml-2 text-xs font-normal text-slate-500">
              ({lexResult.tokens.length} tokens
              {lexResult.errors.length > 0 ? `, ${lexResult.errors.length} error(s)` : ""})
            </span>
          </h2>

          {lexResult.errors.length > 0 && (
            <div className="mb-3 space-y-1">
              {lexResult.errors.map((err, i) => (
                <div
                  key={i}
                  className="rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-700"
                >
                  Line {err.line}, column {err.column}: {err.message}
                </div>
              ))}
            </div>
          )}

          <div className="overflow-x-auto rounded-lg border border-slate-200 max-h-72">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-100 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                    Type
                  </th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                    Value
                  </th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                    Line
                  </th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                    Column
                  </th>
                </tr>
              </thead>
              <tbody>
                {lexResult.tokens.map((token, i) => (
                  <tr key={i} className="odd:bg-white even:bg-slate-50">
                    <td className="px-3 py-1.5 font-mono text-blue-700 border-b border-slate-100">
                      {token.type}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-slate-800 border-b border-slate-100">
                      {token.value}
                    </td>
                    <td className="px-3 py-1.5 text-slate-500 border-b border-slate-100">
                      {token.line}
                    </td>
                    <td className="px-3 py-1.5 text-slate-500 border-b border-slate-100">
                      {token.column}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {analysis && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-2">
            Syntax analysis
            <span className="ml-2 text-xs font-normal text-slate-500">
              {analysis.parse_errors.length > 0
                ? `(${analysis.parse_errors.length} error(s))`
                : "(no syntax errors)"}
            </span>
          </h2>

          {analysis.parse_errors.length > 0 && (
            <div className="mb-3 space-y-1">
              {analysis.parse_errors.map((err, i) => (
                <div
                  key={i}
                  className="rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-700"
                >
                  Line {err.line}, column {err.column}: {err.message}
                </div>
              ))}
            </div>
          )}

          <AstTreeView ast={analysis.ast} />
        </div>
      )}

      {analysis && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-2">
            Semantic analysis
            <span className="ml-2 text-xs font-normal text-slate-500">
              {analysis.semantic_errors.length > 0
                ? `(${analysis.semantic_errors.length} error(s))`
                : "(no semantic errors)"}
            </span>
          </h2>

          {analysis.semantic_errors.length > 0 && (
            <div className="mb-3 space-y-1">
              {analysis.semantic_errors.map((err, i) => (
                <div
                  key={i}
                  className="rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-700"
                >
                  Line {err.line}, column {err.column}: {err.message}
                </div>
              ))}
            </div>
          )}

          <h3 className="text-xs font-semibold text-slate-500 uppercase mb-1">
            Symbol table
          </h3>
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                    Name
                  </th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                    Type
                  </th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                    Scope depth
                  </th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
                    Declared at
                  </th>
                </tr>
              </thead>
              <tbody>
                {analysis.symbols.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-3 py-2 text-slate-400 text-center">
                      No variables declared
                    </td>
                  </tr>
                )}
                {analysis.symbols.map((sym, i) => (
                  <tr key={i} className="odd:bg-white even:bg-slate-50">
                    <td className="px-3 py-1.5 font-mono text-slate-800 border-b border-slate-100">
                      {sym.name}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-blue-700 border-b border-slate-100">
                      {sym.type}
                    </td>
                    <td className="px-3 py-1.5 text-slate-500 border-b border-slate-100">
                      {sym.scope_depth}
                    </td>
                    <td className="px-3 py-1.5 text-slate-500 border-b border-slate-100">
                      {sym.line}:{sym.column}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {analysis && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-2">
            Intermediate code (three-address code)
            <span className="ml-2 text-xs font-normal text-slate-500">
              ({analysis.original.length} instruction{analysis.original.length === 1 ? "" : "s"})
            </span>
          </h2>
          <div className="rounded-lg border border-slate-200 bg-white p-4 overflow-x-auto max-h-96">
            <pre className="font-mono text-sm text-slate-800 leading-6">
              {analysis.original.length === 0
                ? "(no instructions)"
                : analysis.original
                    .map((instr) =>
                      instr.op === "LABEL" ? instr.text : `    ${instr.text}`
                    )
                    .join("\n")}
            </pre>
          </div>
        </div>
      )}

      {analysis && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-2">
            Optimization
            <span className="ml-2 text-xs font-normal text-slate-500">
              (constant folding &amp; propagation &rarr; common subexpression
              elimination &rarr; dead code elimination
              {analysis.instructions_removed > 0
                ? `, ${analysis.instructions_removed} instruction(s) removed`
                : ", nothing to remove here"}
              )
            </span>
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase mb-1">
                Before optimization
              </h3>
              <div className="rounded-lg border border-slate-200 bg-white p-4 overflow-x-auto max-h-96">
                <pre className="font-mono text-sm text-slate-800 leading-6">
                  {analysis.original
                    .map((instr) =>
                      instr.op === "LABEL" ? instr.text : `    ${instr.text}`
                    )
                    .join("\n")}
                </pre>
              </div>
            </div>
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase mb-1">
                After optimization
              </h3>
              <div className="rounded-lg border border-green-200 bg-green-50 p-4 overflow-x-auto max-h-96">
                <pre className="font-mono text-sm text-slate-800 leading-6">
                  {analysis.after_dce.length === 0
                    ? "(fully eliminated)"
                    : analysis.after_dce
                        .map((instr) =>
                          instr.op === "LABEL" ? instr.text : `    ${instr.text}`
                        )
                        .join("\n")}
                </pre>
              </div>
            </div>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-3 text-xs text-slate-500">
            <div>
              After constant folding: {analysis.after_constant_folding.length} instructions
            </div>
            <div>After CSE: {analysis.after_cse.length} instructions</div>
            <div>After dead code elimination: {analysis.after_dce.length} instructions</div>
          </div>
        </div>
      )}
    </div>
  );
}
