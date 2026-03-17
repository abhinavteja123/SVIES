export default function StatusBadge({ level }) {
  const normalized = (level || '').toUpperCase();

  return (
    <span className={`badge badge-${normalized.toLowerCase()}`}>
      {normalized}
    </span>
  );
}
