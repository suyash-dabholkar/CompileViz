// Turns the flat {message, line, column} error lists the backend
// returns into Monaco markers, the squiggly underlines you see under a
// mistake in any real editor, hover for the message.
//
// None of our error objects carry a length (how many characters the
// underline should span), only a starting position. For a LEXER error
// that's fine, "Unexpected character 'x'" is always exactly one
// character. For a PARSER or SEMANTIC error, the mistake is usually a
// specific token (a misspelled keyword, an undeclared identifier), so
// this looks that token up in the token list already fetched for the
// "Lexical analysis" table and uses its actual length, falling back to
// a single character only if no token starts at that exact position
// (e.g. an error reported at end-of-file, past the last real token).

function findTokenAt(tokens, line, column) {
  return tokens.find((t) => t.line === line && t.column === column);
}

function toMarker(monaco, err, tokens, sourceLabel) {
  const token = findTokenAt(tokens, err.line, err.column);
  const length = token ? token.value.length : 1;
  return {
    severity: monaco.MarkerSeverity.Error,
    message: `[${sourceLabel}] ${err.message}`,
    startLineNumber: err.line,
    startColumn: err.column,
    endLineNumber: err.line,
    endColumn: err.column + length,
  };
}

/**
 * Builds the full marker list for one compile result. `tokens` should
 * be the token list from /api/compiler/tokenize for the same source,
 * used only to look up accurate underline widths as described above.
 */
export function buildErrorMarkers(monaco, { lexErrors, parseErrors, semanticErrors, tokens }) {
  return [
    ...lexErrors.map((e) => toMarker(monaco, e, tokens, "Lexer")),
    ...parseErrors.map((e) => toMarker(monaco, e, tokens, "Parser")),
    ...semanticErrors.map((e) => toMarker(monaco, e, tokens, "Semantic")),
  ];
}

export const MARKER_OWNER = "compileviz";
