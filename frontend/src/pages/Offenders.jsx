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
                                                <td colSpan={7} style={{ padding: 20, background: '#111827' }}>
                                                    <strong style={{ fontSize: 13 }}>Violation History ({(historyMap[o.plate] || []).length} records)</strong>
                                                    {(historyMap[o.plate] || []).length > 0 ? (
                                                        <table className="data-table" style={{ marginTop: 10 }}>
                                                            <thead>
                                                                <tr><th>Date</th><th>Violations</th><th>Score</th><th>Level</th></tr>
                                                            </thead>
                                                            <tbody>
                                                                {(historyMap[o.plate] || []).slice(0, 10).map((h, j) => (
                                                                    <tr key={j}>
                                                                        <td style={{ fontSize: 12 }}>{h.timestamp ? new Date(h.timestamp).toLocaleString() : '\u2014'}</td>
                                                                        <td style={{ fontSize: 12 }}>{h.violation_types || '\u2014'}</td>
                                                                        <td>{h.risk_score}</td>
                                                                        <td><span className={`badge badge-${(h.alert_level || 'low').toLowerCase()}`}>{h.alert_level}</span></td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
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
