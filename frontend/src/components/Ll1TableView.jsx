export default function Ll1TableView({ table }) {
  if (!table) return null;
  const { non_terminals: nonTerminals, terminals, table: cells, conflicts } = table;

  const conflictKeys = new Set(
    conflicts.map((c) => `${c.non_terminal}|${c.terminal}`)
  );

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr>
            <th className="px-4 py-2.5 text-left font-medium text-ink-soft border-b border-graph">
              &nbsp;
            </th>
            {terminals.map((terminal) => (
              <th
                key={terminal}
                className="px-4 py-2.5 text-left font-mono font-medium text-ink-soft border-b border-graph"
              >
                {terminal}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {nonTerminals.map((nt) => (
            <tr key={nt} className="odd:bg-white even:bg-paper/60">
              <td className="px-4 py-2 font-mono font-medium text-ink border-b border-graph/60">
                {nt}
              </td>
              {terminals.map((terminal) => {
                const productions = cells[nt]?.[terminal];
                const isConflict = conflictKeys.has(`${nt}|${terminal}`);
                return (
                  <td
                    key={terminal}
                    className={`px-4 py-2 font-mono border-b border-graph/60 ${
                      isConflict ? "bg-signal-light text-signal-dark font-semibold" : "text-ink-soft"
                    }`}
                  >
                    {productions ? productions.join(" / ") : ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
