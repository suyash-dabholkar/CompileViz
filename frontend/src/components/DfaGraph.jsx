import { useMemo } from "react";
import ReactFlow, { Background, Controls, MarkerType } from "reactflow";
import "reactflow/dist/style.css";

/**
 * Turns the DFA JSON shape returned by /api/regex/direct and
 * /api/regex/indirect (dfa.to_dict() on the backend) into react-flow
 * nodes and edges.
 *
 * Layout: a simple BFS-depth layout, states reachable in fewer steps
 * from the start state sit further left, states at the same depth are
 * stacked vertically. No extra layout library needed for graphs this
 * small (a handful to a few dozen states).
 */
function layoutDfa(dfa) {
  const adjacency = {};
  for (const t of dfa.transitions) {
    (adjacency[t.from] ??= []).push(t);
  }

  const depth = { [dfa.start]: 0 };
  const queue = [dfa.start];
  while (queue.length) {
    const current = queue.shift();
    for (const t of adjacency[current] ?? []) {
      if (!(t.to in depth)) {
        depth[t.to] = depth[current] + 1;
        queue.push(t.to);
      }
    }
  }
  // Unreachable-from-start states shouldn't happen for a well-formed DFA,
  // but fall back to depth 0 rather than crashing if one ever shows up.
  for (let i = 0; i < dfa.num_states; i++) {
    if (!(i in depth)) depth[i] = 0;
  }

  const levels = {};
  for (let i = 0; i < dfa.num_states; i++) {
    (levels[depth[i]] ??= []).push(i);
  }

  const X_GAP = 200;
  // More states sharing a depth level need more room between them, or
  // they overlap once react-flow's fitView zooms out to fit them all.
  // 90px is comfortable for a handful of nodes; it shrinks a little for
  // genuinely large levels so the total height stays sane.
  const maxLevelSize = Math.max(...Object.values(levels).map((ids) => ids.length));
  const Y_GAP = maxLevelSize > 20 ? 60 : 90;

  const positions = {};
  for (const [levelDepth, ids] of Object.entries(levels)) {
    ids.forEach((id, idx) => {
      const offset = (ids.length - 1) / 2;
      positions[id] = {
        x: Number(levelDepth) * X_GAP,
        y: (idx - offset) * Y_GAP,
      };
    });
  }
  return { positions, maxLevelSize };
}

function buildNodes(dfa, positions) {
  const acceptingSet = new Set(dfa.accepting);
  const nodes = [];
  for (let id = 0; id < dfa.num_states; id++) {
    const isStart = id === dfa.start;
    const isAccepting = acceptingSet.has(id);
    nodes.push({
      id: String(id),
      position: positions[id],
      data: { label: `q${id}` },
      style: {
        borderRadius: "9999px",
        width: 56,
        height: 56,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 600,
        fontSize: 13,
        fontFamily: "'JetBrains Mono', monospace",
        border: isAccepting ? "3px double #16213A" : "2px solid #16213A",
        background: isStart ? "#E8F0FA" : "#FFFFFF",
        color: "#16213A",
      },
    });
  }
  return nodes;
}

/**
 * Collapses a symbol list into character-range notation when there are
 * more than a few of them, e.g. the 62 symbols in [a-zA-Z0-9] become
 * "0-9, A-Z, a-z" instead of a 62-character label that overflows the
 * diagram. Below the threshold, symbols are listed as-is, since "a, b"
 * is clearer than forcing it into range notation.
 */
function compressSymbols(symbols) {
  const unique = Array.from(new Set(symbols)).sort(
    (a, b) => a.codePointAt(0) - b.codePointAt(0)
  );
  if (unique.length <= 4) return unique.join(", ");

  const formatRange = (start, end) => {
    if (start === end) return start;
    if (end.codePointAt(0) - start.codePointAt(0) === 1) return `${start}, ${end}`;
    return `${start}-${end}`;
  };

  const ranges = [];
  let rangeStart = unique[0];
  let rangeEnd = unique[0];
  for (let i = 1; i < unique.length; i++) {
    const ch = unique[i];
    if (ch.codePointAt(0) === rangeEnd.codePointAt(0) + 1) {
      rangeEnd = ch;
    } else {
      ranges.push(formatRange(rangeStart, rangeEnd));
      rangeStart = ch;
      rangeEnd = ch;
    }
  }
  ranges.push(formatRange(rangeStart, rangeEnd));
  return ranges.join(", ");
}

function buildEdges(dfa) {
  // Group transitions sharing the same (from, to) pair so parallel
  // transitions on different symbols render as one labeled edge instead
  // of overlapping lines.
  const grouped = new Map();
  for (const t of dfa.transitions) {
    const key = `${t.from}->${t.to}`;
    if (!grouped.has(key)) grouped.set(key, { from: t.from, to: t.to, symbols: [] });
    grouped.get(key).symbols.push(t.symbol);
  }
  return Array.from(grouped.values()).map(({ from, to, symbols }) => ({
    id: `${from}-${to}`,
    source: String(from),
    target: String(to),
    label: compressSymbols(symbols),
    markerEnd: { type: MarkerType.ArrowClosed, color: "#16213A" },
    style: { stroke: "#3A4A66" },
    labelStyle: { fontSize: 12, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fill: "#16213A" },
    labelBgStyle: { fill: "#F5F6F2" },
  }));
}

const MIN_HEIGHT = 360;
const MAX_HEIGHT = 720;

/**
 * Re-fits the camera whenever the node set actually changes, instead of
 * relying only on react-flow's `fitView` prop, which fits exactly once
/**
 * Applies a step trace's highlight to already-laid-out nodes and edges.
 *
 * Kept separate from buildNodes/buildEdges, and memoized separately, so
 * that stepping through a trace is a cheap style remap over the existing
 * layout rather than a relayout. Crucially it also does NOT feed into
 * graphIdentity below, so a step change is a plain prop update and the
 * camera stays where it is instead of refitting on every keypress.
 *
 * `highlight` is { states, edges, discovered }:
 *   - states     the step's current state(s), amber
 *   - edges      the step's current edge ids ("0-2"), amber
 *   - discovered the states the trace has reached so far, full opacity
 * Everything else dims. With no highlight at all, nothing changes, which
 * is what the existing non-trace call sites rely on.
 */
const DIM = 0.18;

function applyHighlight(nodes, edges, highlight) {
  if (!highlight) return { nodes, edges };

  const current = new Set((highlight.states ?? []).map(String));
  const activeEdges = new Set(highlight.edges ?? []);
  // No `discovered` key means "everything is in play", so a caller can
  // highlight a step without also tracking reveal order.
  const discovered = highlight.discovered
    ? new Set(highlight.discovered.map(String))
    : null;

  const seen = (id) => discovered === null || discovered.has(id) || current.has(id);

  return {
    nodes: nodes.map((node) => {
      const isCurrent = current.has(node.id);
      return {
        ...node,
        style: {
          ...node.style,
          opacity: seen(node.id) ? 1 : DIM,
          border: isCurrent ? "3px solid #E8A33D" : node.style.border,
          background: isCurrent ? "#FCF1DE" : node.style.background,
        },
      };
    }),
    edges: edges.map((edge) => {
      const isCurrent = activeEdges.has(edge.id);
      const visible = seen(edge.source) && seen(edge.target);
      return {
        ...edge,
        animated: isCurrent,
        style: {
          ...edge.style,
          opacity: isCurrent ? 1 : visible ? 1 : DIM,
          stroke: isCurrent ? "#C6821F" : edge.style.stroke,
          strokeWidth: isCurrent ? 2.5 : undefined,
        },
        labelStyle: {
          ...edge.labelStyle,
          fill: isCurrent ? "#C6821F" : edge.labelStyle.fill,
          opacity: visible ? 1 : DIM,
        },
      };
    }),
  };
}

/**
 * A stable identity for the current DFA's shape, used as a React `key`
 * to force ReactFlow to fully remount whenever a new pattern is built.
 *
 * This is what actually fixes the fitting: react-flow's own `fitView`
 * prop times itself correctly against whatever node set exists at
 * mount, but on an update (same component instance, new nodes/edges
 * props) it does NOT re-fit automatically. Remounting via `key` makes
 * every new DFA look like a brand new mount, so `fitView` always runs
 * fresh against the complete, final set of nodes, including states
 * that would otherwise end up positioned outside the visible pane.
 */
function graphIdentity(dfa) {
  return `${dfa.num_states}-${dfa.start}-${dfa.accepting.join(",")}`;
}

function DfaGraphInner({ dfa, height: baseHeight, highlight }) {
  const { nodes: baseNodes, edges: baseEdges, height } = useMemo(() => {
    if (!dfa) return { nodes: [], edges: [], height: baseHeight };
    const { positions, maxLevelSize } = layoutDfa(dfa);
    // Give large graphs proportionally more vertical room instead of
    // always squeezing them into the same fixed-height box a 2-state
    // graph uses.
    const suggestedHeight = maxLevelSize * 70 + 120;
    return {
      nodes: buildNodes(dfa, positions),
      edges: buildEdges(dfa),
      height: Math.min(MAX_HEIGHT, Math.max(baseHeight, suggestedHeight)),
    };
  }, [dfa, baseHeight]);

  const { nodes, edges } = useMemo(
    () => applyHighlight(baseNodes, baseEdges, highlight),
    [baseNodes, baseEdges, highlight],
  );

  if (!dfa) return null;

  return (
    <div style={{ height }} className="bg-white">
      {/* minZoom is dropped from react-flow's default of 0.5: a wide,
          shallow graph (many states at one depth, or several states
          spread across a long horizontal chain) can need to zoom out
          further than that to fit inside a fixed-height panel with any
          padding at all. Without this, fitView silently clamps to 0.5
          and the rightmost or bottom-most states render outside the
          visible pane even though react-flow "thinks" it fit them. */}
      <ReactFlow
        key={graphIdentity(dfa)}
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#D8DEE9" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export default function DfaGraph({ dfa, height = MIN_HEIGHT, highlight = null }) {
  return <DfaGraphInner dfa={dfa} height={height} highlight={highlight} />;
}
