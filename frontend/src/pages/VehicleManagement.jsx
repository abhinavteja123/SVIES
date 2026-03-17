import { useState, useEffect } from 'react';
import {
  Car, Shield, Search, RefreshCw, Plus, Trash2, Pencil, X, Check,
  ChevronDown, ChevronLeft, ChevronRight, AlertTriangle, CheckCircle, XCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { KPICard, LoadingSpinner, EmptyState } from '../components';

const ROLE_LEVEL = { VIEWER: 0, RTO: 1, POLICE: 2, ADMIN: 3 };
const VEHICLE_TYPES = ['CAR', 'MOTORCYCLE', 'AUTO', 'BUS', 'TRUCK', 'VAN', 'OTHER'];
const STATUS_OPTIONS = ['ACTIVE', 'SUSPENDED', 'BLACKLISTED'];

const STATUS_STYLES = {
  ACTIVE:      { background: 'rgba(34,197,94,0.15)',   color: '#4ade80' },
  SUSPENDED:   { background: 'rgba(245,158,11,0.15)',  color: '#fbbf24' },
  BLACKLISTED: { background: 'rgba(239,68,68,0.15)',   color: '#f87171' },
};

const COMPLIANCE_COLORS = {
  VALID:   'var(--color-success)',
  EXPIRED: 'var(--color-danger)',
  NONE:    'var(--text-muted)',
};

const EMPTY_FORM = {
  plate: '', owner: '', phone: '', email: '', vehicle_type: 'CAR',
  color: '', make: '', year: 2024, state: '', registration_state_code: '', status: 'ACTIVE',
};

export default function VehicleManagement() {
  const { role } = useAuth();
  const roleLevel = ROLE_LEVEL[role] || 0;
  const isAdmin = role === 'ADMIN';
  const canToggleStolen = roleLevel >= ROLE_LEVEL.POLICE;

  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');

  // Add form
  const [showAddForm, setShowAddForm] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [saving, setSaving] = useState(false);

  // Edit state
  const [editPlate, setEditPlate] = useState(null);
  const [editData, setEditData] = useState({});
  const [editSaving, setEditSaving] = useState(false);

  // Inline compliance editing
  const [complianceEdit, setComplianceEdit] = useState(null); // { plate, type: 'pucc'|'insurance' }
  const [complianceForm, setComplianceForm] = useState({});
  const [complianceSaving, setComplianceSaving] = useState(false);

  const [deletingPlate, setDeletingPlate] = useState(null);
  const [stolenToggling, setStolenToggling] = useState(null);

  // ── Fetch ──
  const fetchVehicles = async (p = page, s = search) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getVehicles(p, s);
      setVehicles(data.vehicles || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
      setPage(data.page || 1);
    } catch (err) {
      setError(err.message || 'Failed to load vehicles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchVehicles(1, ''); }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
    fetchVehicles(1, searchInput);
  };

  // ── Add Vehicle ──
  const handleAdd = async (e) => {
    e.preventDefault();
    if (!form.plate || !form.owner) { toast.error('Plate and owner are required'); return; }
    setSaving(true);
    try {
      await api.addVehicle({ ...form, plate: form.plate.toUpperCase().trim() });
      toast.success(`Vehicle ${form.plate.toUpperCase()} registered`);
      setForm({ ...EMPTY_FORM });
      setShowAddForm(false);
      fetchVehicles(1, search);
    } catch (err) {
      toast.error(err.message || 'Failed to add vehicle');
    } finally {
      setSaving(false);
    }
  };

  // ── Edit Vehicle ──
  const startEdit = (v) => {
    setEditPlate(v.plate);
    setEditData({
      owner: v.owner, phone: v.phone, email: v.email, vehicle_type: v.vehicle_type,
      color: v.color, make: v.make, year: v.year, state: v.state,
      registration_state_code: v.registration_state_code, status: v.status,
    });
  };

  const cancelEdit = () => { setEditPlate(null); setEditData({}); };

  const saveEdit = async () => {
    setEditSaving(true);
    try {
      await api.updateVehicle(editPlate, editData);
      toast.success(`Vehicle ${editPlate} updated`);
      setVehicles((prev) => prev.map((v) => v.plate === editPlate ? { ...v, ...editData } : v));
      cancelEdit();
    } catch (err) {
      toast.error(err.message || 'Failed to update vehicle');
    } finally {
      setEditSaving(false);
    }
  };

  // ── Delete ──
  const handleDelete = async (plate) => {
    if (!window.confirm(`Delete vehicle "${plate}" and all related records (PUCC, insurance, stolen)? This cannot be undone.`)) return;
    setDeletingPlate(plate);
    try {
      await api.deleteVehicle(plate);
      toast.success(`Vehicle ${plate} deleted`);
      setVehicles((prev) => prev.filter((v) => v.plate !== plate));
      setTotal((t) => t - 1);
    } catch (err) {
      toast.error(err.message || 'Failed to delete vehicle');
    } finally {
      setDeletingPlate(null);
    }
  };

  // ── Stolen Toggle ──
  const handleStolenToggle = async (plate, currentlyStolen) => {
    const action = currentlyStolen ? 'unmark' : 'mark';
    if (!window.confirm(`${currentlyStolen ? 'Unmark' : 'Mark'} vehicle "${plate}" as stolen?`)) return;
    setStolenToggling(plate);
    try {
      await api.setStolen(plate, !currentlyStolen);
      toast.success(`Vehicle ${plate} ${action}ed as stolen`);
      setVehicles((prev) => prev.map((v) => v.plate === plate ? { ...v, is_stolen: !currentlyStolen } : v));
    } catch (err) {
      toast.error(err.message || 'Failed to update stolen status');
    } finally {
      setStolenToggling(null);
    }
  };

  // ── Compliance (PUCC / Insurance) ──
  const startComplianceEdit = (plate, type, current) => {
    setComplianceEdit({ plate, type });
    if (type === 'pucc') {
      setComplianceForm({ valid_until: current?.valid_until || '', status: current?.status || 'VALID' });
    } else {
      setComplianceForm({ valid_until: current?.valid_until || '', type: current?.type || 'COMPREHENSIVE', status: current?.status || 'VALID' });
    }
  };

  const saveCompliance = async () => {
    setComplianceSaving(true);
    const { plate, type } = complianceEdit;
    try {
      if (type === 'pucc') {
        await api.updatePUCC(plate, complianceForm);
      } else {
        await api.updateInsurance(plate, complianceForm);
      }
      toast.success(`${type.toUpperCase()} updated for ${plate}`);
      setVehicles((prev) => prev.map((v) => v.plate === plate ? { ...v, [type]: { ...complianceForm } } : v));
      setComplianceEdit(null);
    } catch (err) {
      toast.error(err.message || `Failed to update ${type}`);
    } finally {
      setComplianceSaving(false);
    }
  };

  // ── KPIs ──
  const activeCount = vehicles.filter((v) => v.status === 'ACTIVE').length;
  const suspendedCount = vehicles.filter((v) => v.status === 'SUSPENDED' || v.status === 'BLACKLISTED').length;
  const stolenCount = vehicles.filter((v) => v.is_stolen).length;

  const kpis = [
    { label: 'Total Vehicles', value: total, icon: Car, color: '#6366f1' },
    { label: 'Active', value: activeCount, icon: CheckCircle, color: '#4ade80' },
    { label: 'Suspended / BL', value: suspendedCount, icon: AlertTriangle, color: '#fbbf24' },
    { label: 'Stolen', value: stolenCount, icon: XCircle, color: '#f87171' },
  ];

  // ── Access guard ──
  if (roleLevel < ROLE_LEVEL.RTO) {
    return (
      <div className="page">
        <EmptyState icon={Shield} title="Access Denied" message="RTO, Police, and Admin users can manage vehicles." />
      </div>
    );
  }

  if (loading && vehicles.length === 0) return <LoadingSpinner message="Loading vehicles..." />;

  if (error) {
    return (
      <div className="page">
        <div className="page-header"><h2>Vehicle Management</h2></div>
        <div className="card" style={{ padding: '2rem' }}>
          <EmptyState icon={Car} title="Failed to load vehicles" message={error} />
          <div style={{ textAlign: 'center', marginTop: '1rem' }}>
            <button className="btn btn-primary" onClick={() => fetchVehicles()}><RefreshCw size={16} /> Retry</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page vehicle-management">
      <div className="page-header">
        <h2>Vehicle Management</h2>
        <p>Manage vehicle registrations, compliance, and stolen status</p>
      </div>

      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <KPICard key={kpi.label} label={kpi.label} value={kpi.value} icon={kpi.icon} color={kpi.color} />
        ))}
      </div>

      {/* Search Bar */}
      <form className="filter-bar" onSubmit={handleSearch} style={{ marginBottom: '1rem' }}>
        <div className="form-group" style={{ flex: 1 }}>
          <input
            className="form-input"
            placeholder="Search by plate or owner..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </div>
        <button type="submit" className="btn btn-primary"><Search size={16} /> Search</button>
        {search && (
          <button type="button" className="btn btn-secondary" onClick={() => { setSearchInput(''); setSearch(''); fetchVehicles(1, ''); }}>
            Clear
          </button>
        )}
      </form>

      {/* Add Vehicle Form */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title"><Plus size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />Register Vehicle</h3>
          <button className={`btn ${showAddForm ? 'btn-secondary' : 'btn-primary'}`} onClick={() => setShowAddForm(!showAddForm)}>
            {showAddForm ? 'Cancel' : 'Add Vehicle'}
          </button>
        </div>
        {showAddForm && (
          <div className="card-body" style={{ borderTop: '1px solid rgba(148,163,184,0.08)' }}>
            <form onSubmit={handleAdd} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', maxWidth: '900px' }}>
              <div className="form-group">
                <label className="form-label">Plate *</label>
                <input className="form-input form-input-mono" placeholder="AP09AB1234" value={form.plate}
                  onChange={(e) => setForm({ ...form, plate: e.target.value.toUpperCase() })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Owner *</label>
                <input className="form-input" placeholder="Owner name" value={form.owner}
                  onChange={(e) => setForm({ ...form, owner: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Phone</label>
                <input className="form-input" placeholder="+91..." value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input className="form-input" type="email" placeholder="email@example.com" value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Vehicle Type</label>
                <div style={{ position: 'relative' }}>
                  <select className="form-input" value={form.vehicle_type}
                    onChange={(e) => setForm({ ...form, vehicle_type: e.target.value })}
                    style={{ appearance: 'none', paddingRight: '2rem', cursor: 'pointer' }}>
                    {VEHICLE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                  <ChevronDown size={14} style={{ position: 'absolute', right: '0.6rem', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', opacity: 0.5 }} />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Make</label>
                <input className="form-input" placeholder="e.g. Honda" value={form.make}
                  onChange={(e) => setForm({ ...form, make: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Color</label>
                <input className="form-input" placeholder="e.g. Black" value={form.color}
                  onChange={(e) => setForm({ ...form, color: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Year</label>
                <input className="form-input" type="number" min={1900} max={2100} value={form.year}
                  onChange={(e) => setForm({ ...form, year: parseInt(e.target.value) || 2024 })} />
              </div>
              <div className="form-group">
                <label className="form-label">State</label>
                <input className="form-input" placeholder="Telangana" value={form.state}
                  onChange={(e) => setForm({ ...form, state: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">State Code</label>
                <input className="form-input" placeholder="TS" maxLength={5} value={form.registration_state_code}
                  onChange={(e) => setForm({ ...form, registration_state_code: e.target.value.toUpperCase() })} />
              </div>
              <div className="form-group">
                <label className="form-label">Status</label>
                <div style={{ position: 'relative' }}>
                  <select className="form-input" value={form.status}
                    onChange={(e) => setForm({ ...form, status: e.target.value })}
                    style={{ appearance: 'none', paddingRight: '2rem', cursor: 'pointer' }}>
                    {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <ChevronDown size={14} style={{ position: 'absolute', right: '0.6rem', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', opacity: 0.5 }} />
                </div>
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <button className="btn btn-primary" type="submit" disabled={saving} style={{ gap: '8px' }}>
                  <Plus size={16} /> {saving ? 'Registering...' : 'Register Vehicle'}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

      {/* Compliance Edit Modal */}
      {complianceEdit && (
        <div className="card" style={{ border: '1px solid var(--color-accent)', marginBottom: '1rem' }}>
          <div className="card-header">
            <h3 className="card-title">Edit {complianceEdit.type.toUpperCase()} for {complianceEdit.plate}</h3>
            <button className="btn btn-secondary" onClick={() => setComplianceEdit(null)}><X size={16} /> Cancel</button>
          </div>
          <div className="card-body" style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div className="form-group">
              <label className="form-label">Valid Until</label>
              <input className="form-input" type="date" value={complianceForm.valid_until}
                onChange={(e) => setComplianceForm({ ...complianceForm, valid_until: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-input" value={complianceForm.status}
                onChange={(e) => setComplianceForm({ ...complianceForm, status: e.target.value })}
                style={{ appearance: 'none', cursor: 'pointer' }}>
                <option value="VALID">VALID</option>
                <option value="EXPIRED">EXPIRED</option>
              </select>
            </div>
            {complianceEdit.type === 'insurance' && (
              <div className="form-group">
                <label className="form-label">Type</label>
                <select className="form-input" value={complianceForm.type}
                  onChange={(e) => setComplianceForm({ ...complianceForm, type: e.target.value })}
                  style={{ appearance: 'none', cursor: 'pointer' }}>
                  <option value="COMPREHENSIVE">COMPREHENSIVE</option>
                  <option value="THIRD_PARTY">THIRD_PARTY</option>
                </select>
              </div>
            )}
            <button className="btn btn-primary" onClick={saveCompliance} disabled={complianceSaving}>
              <Check size={16} /> {complianceSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      )}

      {/* Vehicle Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Vehicles ({total})</h3>
          <button className="btn btn-secondary" onClick={() => fetchVehicles()}><RefreshCw size={16} /> Refresh</button>
        </div>
        <div className="card-body">
          {vehicles.length === 0 ? (
            <EmptyState icon={Car} title="No vehicles found" message={search ? 'Try a different search term.' : 'Register the first vehicle using the form above.'} />
          ) : (
            <>
              <div className="data-table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Plate</th>
                      <th>Owner</th>
                      <th>Type</th>
                      <th>Make / Color</th>
                      <th>Status</th>
                      <th>PUCC</th>
                      <th>Insurance</th>
                      <th>Stolen</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vehicles.map((v) => (
                      <tr key={v.plate}>
                        {editPlate === v.plate ? (
                          /* ── Editing row ── */
                          <>
                            <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, letterSpacing: 1 }}>{v.plate}</td>
                            <td><input className="form-input" value={editData.owner} onChange={(e) => setEditData({ ...editData, owner: e.target.value })} style={{ minWidth: 120 }} /></td>
                            <td>
                              <select className="form-input" value={editData.vehicle_type} onChange={(e) => setEditData({ ...editData, vehicle_type: e.target.value })} style={{ appearance: 'none', cursor: 'pointer' }}>
                                {VEHICLE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                              </select>
                            </td>
                            <td>
                              <input className="form-input" value={editData.make} onChange={(e) => setEditData({ ...editData, make: e.target.value })} placeholder="Make" style={{ minWidth: 80, marginBottom: 4 }} />
                              <input className="form-input" value={editData.color} onChange={(e) => setEditData({ ...editData, color: e.target.value })} placeholder="Color" style={{ minWidth: 80 }} />
                            </td>
                            <td>
                              <select className="form-input" value={editData.status} onChange={(e) => setEditData({ ...editData, status: e.target.value })} style={{ appearance: 'none', cursor: 'pointer' }}>
                                {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                              </select>
                            </td>
                            <td colSpan={2} style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.75rem' }}>Save first</td>
                            <td>{v.is_stolen ? <XCircle size={14} style={{ color: 'var(--color-danger)' }} /> : '--'}</td>
                            <td>
                              <div style={{ display: 'flex', gap: 6 }}>
                                <button className="btn btn-primary" style={{ padding: '4px 10px' }} onClick={saveEdit} disabled={editSaving}>
                                  <Check size={14} /> {editSaving ? '...' : 'Save'}
                                </button>
                                <button className="btn btn-secondary" style={{ padding: '4px 10px' }} onClick={cancelEdit}><X size={14} /></button>
                              </div>
                            </td>
                          </>
                        ) : (
                          /* ── Display row ── */
                          <>
                            <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, letterSpacing: 1 }}>{v.plate}</td>
                            <td>{v.owner || '--'}</td>
                            <td><span style={{ fontSize: '0.8rem' }}>{v.vehicle_type || '--'}</span></td>
                            <td><span style={{ fontSize: '0.8rem' }}>{[v.make, v.color].filter(Boolean).join(' / ') || '--'}</span></td>
                            <td>
                              <span className="badge" style={STATUS_STYLES[v.status] || STATUS_STYLES.ACTIVE}>
                                {v.status || 'ACTIVE'}
                              </span>
                            </td>
                            <td>
                              <button
                                className="badge"
                                onClick={() => startComplianceEdit(v.plate, 'pucc', v.pucc)}
                                title="Click to edit PUCC"
                                style={{
                                  cursor: 'pointer', border: 'none',
                                  background: v.pucc?.status === 'VALID' ? 'rgba(34,197,94,0.15)' : v.pucc ? 'rgba(239,68,68,0.15)' : 'rgba(148,163,184,0.1)',
                                  color: COMPLIANCE_COLORS[v.pucc?.status] || COMPLIANCE_COLORS.NONE,
                                }}
                              >
                                {v.pucc?.status || 'NONE'}
                              </button>
                            </td>
                            <td>
                              <button
                                className="badge"
                                onClick={() => startComplianceEdit(v.plate, 'insurance', v.insurance)}
                                title="Click to edit Insurance"
                                style={{
                                  cursor: 'pointer', border: 'none',
                                  background: v.insurance?.status === 'VALID' ? 'rgba(34,197,94,0.15)' : v.insurance ? 'rgba(239,68,68,0.15)' : 'rgba(148,163,184,0.1)',
                                  color: COMPLIANCE_COLORS[v.insurance?.status] || COMPLIANCE_COLORS.NONE,
                                }}
                              >
                                {v.insurance?.status || 'NONE'}
                              </button>
                            </td>
                            <td>
                              {canToggleStolen ? (
                                <button
                                  className="badge"
                                  onClick={() => handleStolenToggle(v.plate, v.is_stolen)}
                                  disabled={stolenToggling === v.plate}
                                  title={v.is_stolen ? 'Unmark as stolen' : 'Mark as stolen'}
                                  style={{
                                    cursor: 'pointer', border: 'none',
                                    background: v.is_stolen ? 'rgba(239,68,68,0.15)' : 'rgba(34,197,94,0.15)',
                                    color: v.is_stolen ? 'var(--color-danger)' : 'var(--color-success)',
                                  }}
                                >
                                  {stolenToggling === v.plate ? '...' : v.is_stolen ? 'YES' : 'NO'}
                                </button>
                              ) : (
                                <span style={{ color: v.is_stolen ? 'var(--color-danger)' : 'var(--color-success)', fontWeight: 700, fontSize: '0.8rem' }}>
                                  {v.is_stolen ? 'YES' : 'NO'}
                                </span>
                              )}
                            </td>
                            <td>
                              <div style={{ display: 'flex', gap: 6 }}>
                                <button className="btn btn-icon" title="Edit" onClick={() => startEdit(v)}
                                  style={{ padding: 5, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', color: '#818cf8' }}>
                                  <Pencil size={13} />
                                </button>
                                {isAdmin && (
                                  <button className="btn btn-icon" title={`Delete ${v.plate}`} disabled={deletingPlate === v.plate}
                                    onClick={() => handleDelete(v.plate)}
                                    style={{ padding: 5, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--color-danger)' }}>
                                    <Trash2 size={13} />
                                  </button>
                                )}
                              </div>
                            </td>
                          </>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '12px', marginTop: '1rem' }}>
                  <button className="btn btn-secondary" disabled={page <= 1} onClick={() => { setPage(page - 1); fetchVehicles(page - 1, search); }}>
                    <ChevronLeft size={16} /> Prev
                  </button>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    Page {page} of {totalPages}
                  </span>
                  <button className="btn btn-secondary" disabled={page >= totalPages} onClick={() => { setPage(page + 1); fetchVehicles(page + 1, search); }}>
                    Next <ChevronRight size={16} />
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
