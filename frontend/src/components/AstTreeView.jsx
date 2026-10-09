const SCALAR_ATTR_KEYS = new Set([
  "op",
  "name",
  "callee",
  "var_type",
  "value",
  "literal_type",
  // Regex syntax-tree leaves (app/automata/direct_dfa.tree_to_dict). No
  // compiler AST node has either key, so nothing else changes.
  "symbol",
  "position",
]);

// Keys the regex tree carries for the teaching layer. They are surfaced
// through the `annotate` prop instead of as attribute badges, so they are
// skipped here rather than relying on them happening to be filtered out.
const TRACE_ONLY_KEYS = new Set(["id", "nullable", "firstpos", "lastpos", "followpos", "is_end_marker"]);

function isNodeLike(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value) && "kind" in value;
}

function isNodeList(value) {
  return Array.isArray(value) && value.length > 0 && isNodeLike(value[0]);
}

function AstNode({ node, label, highlight, annotate }) {
  if (node === null || node === undefined) return null;

  const { kind, line, column, ...rest } = node;
  const childEntries = [];
  const attrs = [];

  for (const [key, value] of Object.entries(rest)) {
    if (isNodeLike(value)) {
      childEntries.push([key, [value]]);
    } else if (isNodeList(value)) {
      childEntries.push([key, value]);
    } else if (Array.isArray(value) && value.length === 0) {
      continue; // nothing to show for an empty list of children
    } else if (TRACE_ONLY_KEYS.has(key)) {
      continue; // shown via `annotate`, not as a badge
    } else if (SCALAR_ATTR_KEYS.has(key) && value !== null) {
      attrs.push([key, value]);
    }
  }

  // Trace nodes carry a stable id; compiler AST nodes do not, so those
  // keep the previous index keying and are never highlighted.
  const current = node.id !== undefined && highlight?.includes(node.id);
  const note = annotate ? annotate(node) : null;

  return (
    <div className="font-mono text-sm">
      <div className={current ? "-ml-1 border-l-2 border-signal bg-signal-light pl-1" : undefined}>
        {label && <span className="text-ink-faint mr-1">{label}:</span>}
        <span className={`font-semibold ${current ? "text-ink" : "text-blueprint"}`}>{kind}</span>
        {attrs.map(([key, value]) => (
          <span key={key} className="ml-2 text-xs text-ink-faint">
            {key}=<span className="text-ink-soft">{String(value)}</span>
          </span>
        ))}
        {note && <span className="ml-2 text-xs text-ink-faint">{note}</span>}
      </div>
      {childEntries.map(([key, nodes]) => (
        <div key={key} className="ml-4 border-l border-graph pl-3 mt-0.5">
          {nodes.length > 1 ? (
            <div className="text-xs text-ink-faint mb-0.5">{key}:</div>
          ) : null}
          {nodes.map((n, i) => (
            <AstNode
              key={n.id ?? i}
              node={n}
              label={nodes.length > 1 ? null : key}
              highlight={highlight}
              annotate={annotate}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * `highlight` is a list of node ids to mark as current (regex trees
 * only; compiler AST nodes have no ids). `annotate` is
 * (node) => string | null, rendered as a trailing badge - one function
 * prop instead of teaching this component about followpos.
 */
export default function AstTreeView({ ast, highlight = null, annotate = null }) {
  if (!ast) return null;
  return (
    <div className="overflow-x-auto">
      <AstNode node={ast} highlight={highlight} annotate={annotate} />
    </div>
  );
}
