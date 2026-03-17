import { useState, useEffect, useRef } from 'react';
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  ShieldAlert, AlertTriangle, AlertOctagon, Car, Radio, Database,
} from 'lucide-react';
import { api, connectWebSocket, connectLiveFeed } from '../api';
import { useAuth } from '../context/AuthContext';
import KPICard from '../components/KPICard';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

function AdminBootstrapBanner({ onPromoted }) {
  const [promoting, setPromoting] = useState(false);
  const [done, setDone] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handlePromote = async () => {
    setPromoting(true);
    setErrorMsg('');
    try {
      await api.bootstrapAdmin();
      setDone(true);
      if (onPromoted) onPromoted();
    } catch (err) {
      console.error('Bootstrap failed:', err);
      if (err.message?.includes('404')) {
        setErrorMsg('Backend needs restart. Stop the backend server (Ctrl+C) and run: python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload');
      } else {
        setErrorMsg('Failed: ' + err.message);
      }
    } finally {
      setPromoting(false);
    }
  };

  if (done) {
    return (
      <div className="card" style={{ padding: '16px 24px', marginBottom: 20, borderColor: 'rgba(34,197,94,0.3)', background: 'rgba(34,197,94,0.08)' }}>
        <strong style={{ color: '#22c55e' }}>Role updated to ADMIN.</strong>{' '}
        Sign out and sign back in to see all features:{' '}
        <button className="btn btn-sm btn-primary" onClick={() => window.location.reload()} style={{ marginLeft: 8 }}>Reload Page</button>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: '16px 24px', marginBottom: 20, borderColor: 'rgba(245,158,11,0.3)', background: 'rgba(245,158,11,0.06)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <strong style={{ color: '#f59e0b' }}>You are currently a VIEWER.</strong>{' '}
          <span style={{ color: 'var(--text-secondary)' }}>Most dashboard pages are restricted. Promote yourself to ADMIN to unlock all features.</span>
        </div>
        <button className="btn btn-primary btn-sm" onClick={handlePromote} disabled={promoting}>
          {promoting ? 'Promoting...' : 'Promote to ADMIN'}
        </button>
      </div>
      {errorMsg && (
        <div style={{ marginTop: 10, padding: '10px 14px', borderRadius: 8, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', fontSize: 13, color: '#fca5a5' }}>
          {errorMsg}
        </div>
      )}
    </div>
  );
}

const LEVEL_COLORS = ['#22c55e', '#f59e0b', '#f97316', '#ef4444'];
const LEVEL_KEYS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

function formatDate(raw) {
  if (!raw) return '--';
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return '--';
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  }) + ', ' + d.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

function scoreClass(score) {
  if (score >= 75) return 'score-critical';
  if (score >= 50) return 'score-high';
  if (score >= 25) return 'score-medium';
  return 'score-low';
}

export default function Overview() {
  const { role, refreshRole } = useAuth();

  const [stats, setStats] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [violations, setViolations] = useState([]);
  const [zones, setZones] = useState([]);
  const [liveFrame, setLiveFrame] = useState(null);
  const [liveDetections, setLiveDetections] = useState([]);
  const [liveViolations, setLiveViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [toast, setToast] = useState(null);

  const feedRef = useRef(null);
  const wsCleanupRef = useRef(null);
  const feedCleanupRef = useRef(null);

  /* ---------- toast helper ---------- */
  function showToast(message, type = 'success') {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  }

  /* ---------- data fetching ---------- */
  const loadData = async () => {
    try {
      const [sRes, aRes, vRes, zRes] = await Promise.allSettled([
        api.getStats(),
        api.getAnalytics(),
        api.getViolations({ per_page: 10 }),
        api.getZones(),
      ]);
      if (sRes.status === 'fulfilled') setStats(sRes.value);
      if (aRes.status === 'fulfilled') setAnalytics(aRes.value);
      if (vRes.status === 'fulfilled') setViolations(vRes.value.violations || []);
      if (zRes.status === 'fulfilled') setZones(zRes.value.zones || zRes.value || []);
    } catch (err) {
      console.error('[Overview] Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  /* ---------- mount / unmount ---------- */
  useEffect(() => {
    loadData();

    wsCleanupRef.current = connectWebSocket((msg) => {
      if (msg.type === 'violation') {
        setLiveViolations((prev) => [msg.data, ...prev].slice(0, 5));
      }
    });

    feedCleanupRef.current = connectLiveFeed((data) => {
      if (data.frame) setLiveFrame(data.frame);
      if (data.detections) setLiveDetections(data.detections);
    });

    return () => {
      if (wsCleanupRef.current) wsCleanupRef.current();
      if (feedCleanupRef.current) feedCleanupRef.current();
    };
  }, []);

  /* ---------- seed demo ---------- */
  const handleSeedDemo = async () => {
    setSeeding(true);
    try {
      await api.seedDemo();
      showToast('Demo data seeded successfully');
      setLoading(true);
      await loadData();
    } catch (err) {
      console.error(err);
      showToast(err.message || 'Failed to seed demo data', 'error');
    } finally {
      setSeeding(false);
    }
  };

  /* ---------- loading state ---------- */
  if (loading) {
    return <LoadingSpinner message="Loading command center..." />;
  }

  /* ---------- derived data ---------- */
  const zoneCount = Array.isArray(zones) ? zones.length : 0;

  const kpis = [
    { label: 'Total Violations', value: stats?.total_violations ?? 0, icon: ShieldAlert, color: '#6366f1' },
    { label: 'Critical Alerts', value: stats?.critical ?? 0, icon: AlertOctagon, color: '#ef4444' },
    { label: 'High Alerts', value: stats?.high ?? 0, icon: AlertTriangle, color: '#f97316' },
    { label: 'Medium Alerts', value: stats?.medium ?? 0, icon: AlertTriangle, color: '#f59e0b' },
    { label: 'Unique Vehicles', value: stats?.unique_plates ?? 0, icon: Car, color: '#06b6d4' },
    { label: 'Active Zones', value: zoneCount, icon: Radio, color: '#22c55e' },
  ];

  const trendData = (analytics?.daily_counts || []).map((d) => ({
    date: d.date,
    count: d.count,
  }));

  const pieData = LEVEL_KEYS
    .map((key) => ({
      name: key,
      value: stats?.[key.toLowerCase()] ?? 0,
    }))
    .filter((d) => d.value > 0);

  return (
    <div className="page">
      {/* -- Inline Toast -- */}
      {toast && (
        <div
          className={`badge ${toast.type === 'error' ? 'badge-critical' : 'badge-low'}`}
          style={{
            position: 'fixed',
            top: 24,
            right: 24,
            zIndex: 9999,
            padding: '10px 20px',
            fontSize: '0.85rem',
            animation: 'fadeIn 0.3s ease',
          }}
        >
          {toast.message}
        </div>
      )}

      {/* ================================================================
          PAGE HEADER
          ================================================================ */}
      <div className="page-header">
        <h2>Command Center</h2>
        <p>Real-time vehicle intelligence overview</p>
      </div>

      {/* ── Admin Bootstrap Banner (VIEWER only) ── */}
      {(role === 'VIEWER' || role === 'RTO') && (
        <AdminBootstrapBanner onPromoted={refreshRole} />
      )}

      {/* ================================================================
          KPI GRID
          ================================================================ */}
      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <KPICard
            key={kpi.label}
            label={kpi.label}
            value={kpi.value}
            icon={kpi.icon}
            color={kpi.color}
          />
        ))}
      </div>

      {/* ================================================================
          LIVE FEED + LIVE VIOLATIONS  (two-column)
          ================================================================ */}
      <div className="grid-2 mb-6">
        {/* --- Left: Live Camera Feed --- */}
        <div className="card">
          <div className="card-header">
            <h3>Live Camera Feed</h3>
            <span className="live-indicator">Live</span>
          </div>
          <div className="card-body">
            {liveFrame ? (
              <div ref={feedRef} className="detection-feed">
                <img
                  src={`data:image/jpeg;base64,${liveFrame}`}
                  alt="Live camera feed"
                />
              </div>
            ) : (
              <EmptyState
                icon={Radio}
                title="No active camera feed"
                message="Connect a camera source or start video processing to view the live feed."
              />
            )}
          </div>
        </div>

        {/* --- Right: Real-time Violations --- */}
        <div className="card">
          <div className="card-header">
            <h3>Live Violations</h3>
            <span className="live-indicator">Live</span>
          </div>
          <div className="card-body">
            {liveViolations.length === 0 ? (
              <EmptyState
                icon={ShieldAlert}
                title="Awaiting violations..."
                message="Live detections will appear here as they occur."
              />
            ) : (
              <div className="detection-panel">
                {liveViolations.map((v, idx) => (
                  <div className="detection-card" key={idx}>
                    <div className="detection-card-header">
                      <span className="detection-card-plate">{v.plate}</span>
                      <StatusBadge level={v.alert_level} />
                    </div>
                    <div className="pipeline-step-detail">
                      {formatDate(v.timestamp)}
                    </div>
                    {v.violations && v.violations.length > 0 && (
                      <div className="pipeline-step-flags">
                        {v.violations.map((flag, fi) => (
                          <span className="pipeline-flag" key={fi}>{flag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ================================================================
          CHARTS ROW
          ================================================================ */}
      <div className="charts-grid">
        {/* --- Left: Violations Trend --- */}
        <div className="chart-card">
          <h3>Violations Trend</h3>
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(d) => d.slice(5)}
                />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#6366f1"
                  fill="url(#areaGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState
              icon={Database}
              title="No trend data"
              message="Trend data will appear after violations are recorded."
            />
          )}
        </div>

        {/* --- Right: Alert Distribution (Donut) --- */}
        <div className="chart-card">
          <h3>Alert Distribution</h3>
          {pieData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    dataKey="value"
                    nameKey="name"
                    paddingAngle={4}
                  >
                    {pieData.map((d) => (
                      <Cell
                        key={d.name}
                        fill={LEVEL_COLORS[LEVEL_KEYS.indexOf(d.name)]}
                        stroke="transparent"
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-center" style={{ gap: 16, marginTop: 8 }}>
                {pieData.map((d) => (
                  <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem' }}>
                    <span
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        background: LEVEL_COLORS[LEVEL_KEYS.indexOf(d.name)],
                        display: 'inline-block',
                      }}
                    />
                    <span style={{ color: 'var(--text-secondary)' }}>{d.name}: {d.value}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <EmptyState
              icon={Database}
              title="No distribution data"
              message="Alert distribution will populate once violations are recorded."
            />
          )}
        </div>
      </div>

      {/* ================================================================
          RECENT VIOLATIONS TABLE
          ================================================================ */}
      <div className="card mb-6">
        <div className="card-header">
          <h3>Recent Activity</h3>
          {role && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleSeedDemo}
              disabled={seeding}
            >
              <Database size={14} />
              {seeding ? 'Seeding...' : 'Seed Demo Data'}
            </button>
          )}
        </div>
        <div className="card-body">
          {violations.length === 0 ? (
            <EmptyState
              icon={ShieldAlert}
              title="No recent violations"
              message="Violations will appear here after the detection pipeline processes data."
            />
          ) : (
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Plate</th>
                    <th>Time</th>
                    <th>Violations</th>
                    <th>Score</th>
                    <th>Level</th>
                  </tr>
                </thead>
                <tbody>
                  {violations.map((v, i) => (
                    <tr key={i}>
                      <td className="plate-cell">{v.plate}</td>
                      <td>{formatDate(v.timestamp)}</td>
                      <td>{v.violation_types || '--'}</td>
                      <td className={`score-cell ${scoreClass(v.risk_score)}`}>
                        {v.risk_score ?? 0}
                      </td>
                      <td>
                        <StatusBadge level={v.alert_level || 'LOW'} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
