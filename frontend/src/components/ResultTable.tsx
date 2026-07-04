interface Props {
  rows: Record<string, unknown>[];
}

export function ResultTable({ rows }: Props) {
  if (rows.length === 0) return null;
  const columns = Object.keys(rows[0]);

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="text-xs w-full">
        <thead className="bg-slate-800">
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="px-3 py-2 text-left text-slate-400 font-medium whitespace-nowrap"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700/50">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-slate-800/40 transition-colors">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 text-slate-300 whitespace-nowrap">
                  {row[col] == null ? (
                    <span className="text-slate-600 italic">null</span>
                  ) : (
                    String(row[col])
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
