import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { BarChart3, Clock, Gauge, Shield } from 'lucide-react';
import { api } from '../api';
import { LoadingSpinner } from '../components';

const LEVEL_COLORS = {
  LOW: '#22c55e',
  MEDIUM: '#f59e0b',
  HIGH: '#f97316',
  CRITICAL: '#dc2626',
};

const TOOLTIP_STYLE = {
  background: '#1a1f35',
  border: '1px solid #2a3050',
  borderRadius: 8,
};

export default function Analytics() {
  const [data, setData] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  /* ── Fetch analytics + stats when time range changes ── */
  useEffect(() => {
    setLoading(true);
    Promise.all([api.getAnalytics(days), api.getStats(days)])
      .then(([analytics, s]) => {
        setData(analytics);
        setStats(s);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [days]);

  /* ── Helpers ── */
  const cleanLabel = (str) =>
    str
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());

  const scoreBinColor = (low) => {
    if (low >= 60) return '#dc2626';
    if (low >= 40) return '#f97316';
    if (low >= 20) return '#f59e0b';
    return '#22c55e';
  };

  /* ── Chart data derivations ── */
  const typeData = stats?.violation_types
    ? Object.entries(stats.violation_types)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
        .map(([name, count]) => ({ name: cleanLabel(name), count }))
    : [];

  // Score histogram — bin raw scores into 10 groups
  const scoreRaw = data?.score_distribution || [];
  const bins = Array.from({ length: 10 }, (_, i) => {
    const low = i * 10;
    const high = low + 10;
    return {
      range: `${low}-${high}`,
      low,
      count: scoreRaw.filter((s) => s >= low && (s < high || (high === 100 && s === 100))).length,
    };
  });

  const hourlyData = (data?.hourly_counts || []).map((h) => ({
    ...h,
    label: `${String(h.hour).padStart(2, '0')}:00`,
  }));

  const levelBars = data?.level_distribution
    ? ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        .map((level) => ({
          level,
          count: data.level_distribution[level] || 0,
        }))
    : [];

  /* ═══════════════════════ Render ═══════════════════════ */
  if (loading) {
    return (
      <div className="page">
        <LoadingSpinner message="Loading analytics..." />
      </div>
    );
  }

  return (
    <div className="page">
      {/* ── Header ── */}
      <div className="page-header flex-between">
        <div>
          <h2>Analytics</h2>
          <p>Violation patterns and enforcement insights</p>
        </div>

        {/* ── Time range selector ── */}
        <div className="flex-gap">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              className={`btn ${days === d ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setDays(d)}
            >
              {d} Days
            </button>
          ))}
        </div>
      </div>

      {/* ── 2x2 Charts Grid ── */}
      <div className="charts-grid">
        {/* ── Chart 1: Top Violation Types (horizontal bar) ── */}
        <div className="chart-card">
          <h3>
            <BarChart3 size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            Top Violation Types
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={typeData} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3050" />
              <XAxis type="number" stroke="#64748b" fontSize={11} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#64748b"
                fontSize={11}
                width={140}
              />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* ── Chart 2: Risk Score Distribution (histogram) ── */}
        <div className="chart-card">
          <h3>
            <Gauge size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            Risk Score Distribution
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={bins}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3050" />
              <XAxis dataKey="range" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {bins.map((d, i) => (
                  <Cell key={i} fill={scoreBinColor(d.low)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* ── Chart 3: Hourly Activity ── */}
        <div className="chart-card">
          <h3>
            <Clock size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            Hourly Activity
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3050" />
              <XAxis
                dataKey="label"
                stroke="#64748b"
                fontSize={11}
              />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelFormatter={(l) => `${l} - ${l.replace(':00', ':59')}`}
              />
              <Bar dataKey="count" fill="#06b6d4" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* ── Chart 4: Alert Level Distribution ── */}
        <div className="chart-card">
          <h3>
            <Shield size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            Alert Level Distribution
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={levelBars}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3050" />
              <XAxis dataKey="level" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {levelBars.map((d, i) => (
                  <Cell key={i} fill={LEVEL_COLORS[d.level] || '#6366f1'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
