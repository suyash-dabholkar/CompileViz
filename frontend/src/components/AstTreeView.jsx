const SCALAR_ATTR_KEYS = new Set(["op", "name", "callee", "var_type", "value", "literal_type"]);

function isNodeLike(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value) && "kind" in value;
}

function isNodeList(value) {
  return Array.isArray(value) && value.length > 0 && isNodeLike(value[0]);
}

function AstNode({ node, label }) {
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
    } else if (SCALAR_ATTR_KEYS.has(key) && value !== null) {
      attrs.push([key, value]);
    }
  }

  return (
    <div className="font-mono text-sm">
      <div>
        {label && <span className="text-slate-400 mr-1">{label}:</span>}
        <span className="font-semibold text-blue-700">{kind}</span>
        {attrs.map(([key, value]) => (
          <span key={key} className="ml-2 text-xs text-slate-500">
            {key}=<span className="text-slate-700">{String(value)}</span>
          </span>
        ))}
      </div>
      {childEntries.map(([key, nodes]) => (
        <div key={key} className="ml-4 border-l border-slate-200 pl-3 mt-0.5">
          {nodes.length > 1 ? (
            <div className="text-xs text-slate-400 mb-0.5">{key}:</div>
          ) : null}
          {nodes.map((n, i) => (
            <AstNode key={i} node={n} label={nodes.length > 1 ? null : key} />
          ))}
        </div>
      ))}
    </div>
  );
}

export default function AstTreeView({ ast }) {
  if (!ast) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 overflow-x-auto">
      <AstNode node={ast} />
    </div>
  );
}
