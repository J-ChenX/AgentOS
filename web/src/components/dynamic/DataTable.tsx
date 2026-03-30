interface DataTableProps {
  columns: string[];
  rows: Record<string, unknown>[];
}

export default function DataTable({ columns, rows }: DataTableProps) {
  return (
    <div className="overflow-x-auto rounded" style={{ border: '1px solid var(--color-border-default)' }}>
      <table className="w-full text-xs">
        <thead>
          <tr style={{ background: 'var(--color-bg-raised)' }}>
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 text-left font-medium" style={{ color: 'var(--color-ink-secondary)' }}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderTop: '1px solid var(--color-border-default)' }}>
              {columns.map((col) => (
                <td key={col} className="px-3 py-2" style={{ color: 'var(--color-ink-primary)' }}>{String(row[col] ?? '')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
