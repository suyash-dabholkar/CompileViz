export default function Ll1TableView({ table }) {
  if (!table) return null;
  const { non_terminals: nonTerminals, terminals, table: cells, conflicts } = table;

  const conflictKeys = new Set(
    conflicts.map((c) => `${c.non_terminal}|${c.terminal}`)
  );

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-100">
          <tr>
            <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
              &nbsp;
            </th>
            {terminals.map((terminal) => (
              <th
                key={terminal}
                className="px-3 py-2 text-left font-mono font-semibold text-slate-700 border-b border-slate-200"
              >
                {terminal}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {nonTerminals.map((nt) => (
            <tr key={nt} className="odd:bg-white even:bg-slate-50">
              <td className="px-3 py-2 font-mono font-semibold text-slate-800 border-b border-slate-100">
                {nt}
              </td>
              {terminals.map((terminal) => {
                const productions = cells[nt]?.[terminal];
                const isConflict = conflictKeys.has(`${nt}|${terminal}`);
                return (
                  <td
                    key={terminal}
                    className={`px-3 py-2 font-mono border-b border-slate-100 ${
                      isConflict ? "bg-red-100 text-red-800 font-semibold" : "text-slate-700"
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
