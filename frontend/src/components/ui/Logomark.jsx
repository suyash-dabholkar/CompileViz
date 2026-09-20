/**
 * The wordmark's icon is a tiny two-state automaton (start state,
 * transition arrow, accepting state, drawn as a double circle),
 * the exact visual grammar the app's own DFA diagrams use. Not a
 * generic icon-font glyph, it's the actual subject matter of the
 * tool, in miniature.
 */
export function Logomark({ className = "" }) {
  return (
    <svg viewBox="0 0 44 24" className={className} fill="none" aria-hidden="true">
      <circle cx="7" cy="12" r="6" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M13 12H31"
        stroke="currentColor"
        strokeWidth="1.6"
        markerEnd="url(#logomark-arrow)"
      />
      <circle cx="37" cy="12" r="6" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="37" cy="12" r="3.4" stroke="currentColor" strokeWidth="1.6" />
      <defs>
        <marker
          id="logomark-arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M0 0L10 5L0 10Z" fill="currentColor" />
        </marker>
      </defs>
    </svg>
  );
}
