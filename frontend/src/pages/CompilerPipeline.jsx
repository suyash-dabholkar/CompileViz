import { useState } from "react";
import AstTreeView from "../components/AstTreeView";
import { parseSource, tokenizeSource } from "../api/compilerApi";
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
}`;

// This page grows one phase at a time: Milestone 7 added the lexer
// section, Milestone 8 adds syntax analysis (the AST) below it.
// Milestone 9 (semantic analysis) and beyond each add their own
// section here, all reading from the same source textarea, matching
// the PRD's tabbed dashboard where every phase updates live from one
// piece of source code.
export default function CompilerPipeline() {
  const [source, setSource] = useState(DEFAULT_SOURCE);
  const [lexResult, setLexResult] = useState(null);
  const [parseResult, setParseResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleCompile(e) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const [lex, parsed] = await Promise.all([
        tokenizeSource(source),
        parseSource(source),
      ]);
      setLexResult(lex);
      setParseResult(parsed);
    } catch (err) {
      setError(extractErrorMessage(err));
      setLexResult(null);
      setParseResult(null);
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
          phase. Lexical and syntax analysis are live now, more phases
          (semantic analysis, and beyond) get added here as they're built.
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

      {parseResult && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-2">
            Syntax analysis
            <span className="ml-2 text-xs font-normal text-slate-500">
              {parseResult.parse_errors.length > 0
                ? `(${parseResult.parse_errors.length} error(s))`
                : "(no syntax errors)"}
            </span>
          </h2>

          {parseResult.parse_errors.length > 0 && (
            <div className="mb-3 space-y-1">
              {parseResult.parse_errors.map((err, i) => (
                <div
                  key={i}
                  className="rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-700"
                >
                  Line {err.line}, column {err.column}: {err.message}
                </div>
              ))}
            </div>
          )}

          <AstTreeView ast={parseResult.ast} />
        </div>
      )}
    </div>
  );
}
