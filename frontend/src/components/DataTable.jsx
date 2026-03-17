import EmptyState from './EmptyState';
import { Database } from 'lucide-react';

export default function DataTable({ columns, data, emptyMessage }) {
  if (!data || data.length === 0) {
    return (
      <EmptyState
        icon={Database}
        title="No data"
        message={emptyMessage || 'No records to display.'}
      />
    );
  }

  return (
    <div className="data-table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr key={row.id ?? rowIdx}>
              {columns.map((col) => (
                <td key={col.key}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
