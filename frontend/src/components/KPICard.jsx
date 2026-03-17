export default function KPICard({ label, value, icon: Icon, color, change }) {
  return (
    <div
      className="kpi-card"
      style={{
        '--kpi-color': color,
        '--kpi-bg': color ? `${color}15` : undefined,
      }}
    >
      <div className="kpi-icon">
        <Icon />
      </div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {change && <div className="kpi-change">{change}</div>}
    </div>
  );
}
