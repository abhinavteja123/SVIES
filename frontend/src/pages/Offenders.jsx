import { useState, useEffect, Fragment } from 'react';
import { Download } from 'lucide-react';
import { api } from '../api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';

export default function Offenders() {
    const [offenders, setOffenders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(null);
    const [historyMap, setHistoryMap] = useState({});
    const [exporting, setExporting] = useState(false);

    useEffect(() => {
        api.getOffenders(20, 30)
            .then(d => setOffenders(d.offenders || []))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    const handleExpand = async (plate) => {
        if (expanded === plate) { setExpanded(null); return; }
        setExpanded(plate);
        if (historyMap[plate]) return;
        try {
            const v = await api.getVehicle(plate, 90);
            setHistoryMap(prev => ({ ...prev, [plate]: v.violation_history || [] }));
        } catch (e) {
            console.error(e);
            setHistoryMap(prev => ({ ...prev, [plate]: [] }));
        }
    };

    const handleSummons = async (plate) => {
        try {
            await api.generateReport(plate);
            toast.success('Court summons PDF downloaded');
        } catch (err) {
            toast.error(err.message || 'Failed to generate summons');
        }
    };

    const handleExport = async (format) => {
        setExporting(true);
        try {
            await api.exportOffenders({ days: 30, limit: 50 }, format);
            toast.success(`Offenders exported as ${format.toUpperCase()}`);
        } catch (err) {
            toast.error(err.message || 'Export failed');
        } finally {
            setExporting(false);
        }
    };

    if (loading) return <div className="loading"><div className="spinner"></div>Loading offenders...</div>;

    const levelLabel = (l) => {
        const labels = { 0: 'Clean', 1: 'Standard', 2: 'Escalated', 3: 'Red Flag' };
        const colors = { 0: '#22c55e', 1: '#f59e0b', 2: '#f97316', 3: '#dc2626' };
        return <span style={{ color: colors[l] || '#94a3b8', fontWeight: 700 }}>{labels[l] || `L${l}`}</span>;
    };

    const chartData = offenders.slice(0, 10).map(o => ({
        plate: o.plate,
        count: o.count,
    }));

    return (
        <div className="page">
            <div className="page-header">
                <div>
                    <h2>Repeat Offender Leaderboard</h2>
                    <p>Top violators in the last 30 days — escalation levels auto-assigned</p>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-secondary" disabled={exporting || offenders.length === 0}
                        onClick={() => handleExport('csv')}>
                        <Download size={16} /> CSV
                    </button>
                    <button className="btn btn-secondary" disabled={exporting || offenders.length === 0}
                        onClick={() => handleExport('pdf')}>
                        <Download size={16} /> PDF
                    </button>
                </div>
            </div>

            {chartData.length > 0 && (
                <div className="card" style={{ marginBottom: 24 }}>
                    <div className="card-header"><h3>Top 10 Offenders</h3></div>
                    <div className="card-body">
                        <ResponsiveContainer width="100%" height={250}>
                            <BarChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#2a3050" />
                                <XAxis dataKey="plate" stroke="#64748b" fontSize={10} />
                                <YAxis stroke="#64748b" fontSize={11} />
                                <Tooltip contentStyle={{ background: '#1a1f35', border: '1px solid #2a3050', borderRadius: 8 }} />
                                <Bar dataKey="count" fill="#ef4444" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            <div className="card">
                {offenders.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-title">No repeat offenders</div>
                        <div className="empty-state-text">No vehicles with multiple violations in the selected period</div>
                    </div>
                ) : (
                    <div className="card-body">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>#</th><th>Plate</th><th>Owner</th><th>Type</th>
                                    <th>Violations</th><th>Level</th><th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {offenders.map((o, i) => (
                                    <Fragment key={o.plate}>
                                        <tr>
                                            <td style={{ fontWeight: 700, color: '#6366f1' }}>{i + 1}</td>
                                            <td style={{ fontWeight: 600, fontFamily: 'monospace' }}>{o.plate}</td>
                                            <td>{o.owner || '\u2014'}</td>
                                            <td>{o.vehicle_type || '\u2014'}</td>
                                            <td style={{ fontWeight: 700, fontSize: 18 }}>{o.count}</td>
                                            <td>{levelLabel(o.level)}</td>
                                            <td>
                                                <button className="btn btn-secondary btn-sm"
                                                    onClick={() => handleExpand(o.plate)}>
                                                    {expanded === o.plate ? 'Close' : 'History'}
                                                </button>
                                                {o.level >= 3 && (
                                                    <button
                                                        className="btn btn-primary btn-sm"
                                                        style={{ marginLeft: 8 }}
                                                        onClick={() => handleSummons(o.plate)}
                                                    >
                                                        Summons
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                        {expanded === o.plate && (
                                            <tr>
                                                <td colSpan={7} style={{ padding: '16px 20px', background: '#0f172a', borderTop: '2px solid #1e293b' }}>
                                                    <strong style={{ fontSize: 13, color: '#e2e8f0', display: 'block', marginBottom: 10 }}>
                                                        Violation History — {o.plate} &nbsp;({(historyMap[o.plate] || []).length} records)
                                                    </strong>
                                                    {(historyMap[o.plate] || []).length > 0 ? (
                                                        <div style={{ overflowX: 'auto', borderRadius: 8, border: '1px solid #1e293b' }}>
                                                            <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
                                                                <colgroup>
                                                                    <col style={{ width: '160px' }} />
                                                                    <col style={{ width: 'auto' }} />
                                                                    <col style={{ width: '60px' }} />
                                                                    <col style={{ width: '90px' }} />
                                                                </colgroup>
                                                                <thead>
                                                                    <tr style={{ background: '#1e293b' }}>
                                                                        <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 11, color: '#94a3b8', fontWeight: 600, letterSpacing: '0.05em' }}>DATE</th>
                                                                        <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 11, color: '#94a3b8', fontWeight: 600, letterSpacing: '0.05em' }}>VIOLATIONS</th>
                                                                        <th style={{ padding: '8px 12px', textAlign: 'center', fontSize: 11, color: '#94a3b8', fontWeight: 600, letterSpacing: '0.05em' }}>SCORE</th>
                                                                        <th style={{ padding: '8px 12px', textAlign: 'center', fontSize: 11, color: '#94a3b8', fontWeight: 600, letterSpacing: '0.05em' }}>LEVEL</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {(historyMap[o.plate] || []).slice(0, 15).map((h, j) => (
                                                                        <tr key={j} style={{ borderTop: '1px solid #1e293b', background: j % 2 === 0 ? '#111827' : '#0f172a' }}>
                                                                            <td style={{ padding: '8px 12px', fontSize: 12, color: '#cbd5e1', whiteSpace: 'nowrap' }}>
                                                                                {h.timestamp ? new Date(h.timestamp).toLocaleString() : '—'}
                                                                            </td>
                                                                            <td style={{
                                                                                padding: '8px 12px',
                                                                                fontSize: 11,
                                                                                color: '#94a3b8',
                                                                                wordBreak: 'break-word',
                                                                                whiteSpace: 'normal',
                                                                                lineHeight: '1.5',
                                                                            }}>
                                                                                {(h.violation_types || '—')
                                                                                    .split(',')
                                                                                    .map((v, vi) => (
                                                                                        <span key={vi} style={{
                                                                                            display: 'inline-block',
                                                                                            background: '#1e293b',
                                                                                            color: '#93c5fd',
                                                                                            borderRadius: 4,
                                                                                            padding: '1px 6px',
                                                                                            margin: '2px 3px 2px 0',
                                                                                            fontSize: 10,
                                                                                            fontFamily: 'monospace',
                                                                                        }}>{v.trim()}</span>
                                                                                    ))
                                                                                }
                                                                            </td>
                                                                            <td style={{ padding: '8px 12px', textAlign: 'center', fontSize: 13, fontWeight: 700, color: '#f1f5f9' }}>
                                                                                {h.risk_score}
                                                                            </td>
                                                                            <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                                                                                <span style={{
                                                                                    fontSize: 11,
                                                                                    fontWeight: 700,
                                                                                    padding: '3px 8px',
                                                                                    borderRadius: 12,
                                                                                    background: {
                                                                                        CRITICAL: '#450a0a', HIGH: '#431407',
                                                                                        MEDIUM: '#422006', LOW: '#052e16'
                                                                                    }[h.alert_level] || '#1e293b',
                                                                                    color: {
                                                                                        CRITICAL: '#f87171', HIGH: '#fb923c',
                                                                                        MEDIUM: '#fbbf24', LOW: '#4ade80'
                                                                                    }[h.alert_level] || '#94a3b8',
                                                                                }}>
                                                                                    {h.alert_level || '—'}
                                                                                </span>
                                                                            </td>
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    ) : <p style={{ color: '#64748b', marginTop: 8 }}>No records found.</p>}
                                                </td>
                                            </tr>
                                        )}
                                    </Fragment>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
