import { useState, useRef } from 'react';
import {
  Search, Upload, Car, Shield, FileText,
  AlertTriangle, CheckCircle, XCircle,
} from 'lucide-react';
import { api } from '../api';
import { StatusBadge, KPICard, LoadingSpinner, EmptyState } from '../components';
import toast from 'react-hot-toast';

export default function VehicleLookup() {
  const [plate, setPlate] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [imageResult, setImageResult] = useState(null);
  const [imageLoading, setImageLoading] = useState(false);
  const fileRef = useRef(null);

  /* ── Plate text search ── */
  const handleSearch = async (e) => {
    e.preventDefault();
    const p = plate.toUpperCase().trim();
    if (!p) return;
    setLoading(true);
    setError('');
    setData(null);
    setImageResult(null);
    try {
      const result = await api.getVehicle(p);
      setData(result);
      toast.success(`Found record for ${p}`);
    } catch (err) {
      setError('Vehicle not found or API error');
      toast.error('Lookup failed');
    } finally {
      setLoading(false);
    }
  };

  /* ── Photo-based plate detection ── */
  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImageLoading(true);
    setError('');
    setImageResult(null);
    setData(null);
    try {
      const res = await api.processImage(file);
      setImageResult(res);
      toast.success('Image processed');
    } catch (err) {
      setError('Failed to process image');
      toast.error('Image processing failed');
    } finally {
      setImageLoading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  /* ── Lookup a specific detected plate ── */
  const lookupDetected = async (p) => {
    setPlate(p);
    setLoading(true);
    setError('');
    try {
      const result = await api.getVehicle(p);
      setData(result);
      toast.success(`Found record for ${p}`);
    } catch {
      setError('Vehicle not found');
      toast.error('Lookup failed');
    } finally {
      setLoading(false);
    }
  };

  /* ── Helpers ── */
  const statusColor = (s) => {
    if (s === 'ACTIVE' || s === 'VALID') return 'var(--color-success)';
    if (s === 'SUSPENDED' || s === 'EXPIRED') return 'var(--color-warning)';
    if (s === 'BLACKLISTED') return 'var(--color-danger)';
    return 'var(--text-muted)';
  };

  const offenderDots = (level) => {
    const max = 4;
    return Array.from({ length: max }, (_, i) => {
      const active = i < level;
      const danger = active && level >= 3;
      return (
        <span
          key={i}
          className={`offender-dot${active ? ' active' : ''}${danger ? ' danger' : ''}`}
        />
      );
    });
  };

  const cleanViolation = (v) =>
    v.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  /* ═══════════════════════ Render ═══════════════════════ */
  return (
    <div className="page">
      {/* ── Header ── */}
      <div className="page-header">
        <h2>Vehicle Lookup</h2>
        <p>Search by plate number or upload photo</p>
      </div>

      {/* ── Search bar ── */}
      <form className="filter-bar" onSubmit={handleSearch}>
        <div className="form-group">
          <input
            className="form-input form-input-mono"
            placeholder="Enter plate e.g. TS09EF1234"
            value={plate}
            onChange={(e) => setPlate(e.target.value)}
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={loading || !plate.trim()}>
          <Search size={16} />
          {loading ? 'Searching...' : 'Search'}
        </button>

        <span className="form-label">OR</span>

        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          hidden
          onChange={handleImageUpload}
        />
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => fileRef.current?.click()}
          disabled={imageLoading}
        >
          <Upload size={16} />
          {imageLoading ? 'Reading plate...' : 'Upload Photo'}
        </button>
      </form>

      {/* ── Loading state ── */}
      {(loading || imageLoading) && (
        <LoadingSpinner message={loading ? 'Looking up vehicle...' : 'Processing image...'} />
      )}

      {/* ── Error state ── */}
      {error && (
        <div className="card card-body mb-4">
          <div className="flex-gap" style={{ alignItems: 'center', color: 'var(--color-danger)' }}>
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* ── Image detection results ── */}
      {imageResult && (
        <div className="card card-body mb-4">
          <h3 className="mb-4">Detected Plates from Image</h3>
          {imageResult.annotated_image && (
            <img
              src={imageResult.annotated_image}
              alt="Detection result"
              className="mb-4"
              style={{ maxHeight: 220, borderRadius: 'var(--radius-md)', border: 'var(--glass-border)' }}
            />
          )}
          <div className="flex-gap" style={{ flexWrap: 'wrap' }}>
            {(imageResult.pipeline_results || []).map((vp, i) => (
              <div key={i} className="card card-body flex-gap" style={{ alignItems: 'center', padding: '10px 16px' }}>
                <Car size={16} />
                <span className="form-input-mono" style={{ fontWeight: 700, letterSpacing: 2 }}>
                  {vp.plate || 'NOT DETECTED'}
                </span>
                {vp.vehicle_type && (
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {vp.vehicle_type}
                  </span>
                )}
                {vp.plate && (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => lookupDetected(vp.plate)}
                  >
                    <Search size={14} /> Lookup
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── No results yet ── */}
      {!data && !loading && !error && !imageResult && (
        <EmptyState
          icon={<Car size={28} />}
          title="No Vehicle Selected"
          text="Enter a plate number above or upload an image to begin lookup"
        />
      )}

      {/* ═══════════ Vehicle data ═══════════ */}
      {data && (
        <>
          {/* ── Two-column info grid ── */}
          <div className="vehicle-info-grid">
            {/* ── Left: VAHAN Registration ── */}
            <div className="card card-body">
              <h3 className="mb-4">
                <FileText size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                VAHAN Registration
              </h3>

              {data.vahan ? (
                <>
                  <div className="info-row">
                    <span className="info-label">Owner</span>
                    <span className="info-value">{data.vahan.owner}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Phone</span>
                    <span className="info-value">{data.vahan.phone}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Vehicle Type</span>
                    <span className="info-value">{data.vahan.vehicle_type}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Make</span>
                    <span className="info-value">{data.vahan.make}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Color</span>
                    <span className="info-value">{data.vahan.color}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Year</span>
                    <span className="info-value">{data.vahan.year}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">State</span>
                    <span className="info-value">{data.vahan.state}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Status</span>
                    <span className="info-value" style={{ color: statusColor(data.vahan.status), fontWeight: 700 }}>
                      {data.vahan.status === 'ACTIVE' && <CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />}
                      {data.vahan.status === 'SUSPENDED' && <AlertTriangle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />}
                      {data.vahan.status === 'BLACKLISTED' && <XCircle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />}
                      {data.vahan.status}
                    </span>
                  </div>
                </>
              ) : (
                <EmptyState
                  icon={<XCircle size={28} />}
                  title="Not Registered"
                  text="Vehicle not found in VAHAN database"
                />
              )}
            </div>

            {/* ── Right: Compliance Status ── */}
            <div className="card card-body">
              <h3 className="mb-4">
                <Shield size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                Compliance Status
              </h3>

              {/* PUCC */}
              <div className="info-row">
                <span className="info-label">PUCC</span>
                <span className="info-value" style={{ color: statusColor(data.pucc?.status) }}>
                  {data.pucc?.status === 'VALID' && <CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />}
                  {data.pucc?.status === 'EXPIRED' && <XCircle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />}
                  {data.pucc?.status || 'NOT FOUND'}
                  {data.pucc?.valid_until && ` (until ${data.pucc.valid_until})`}
                </span>
              </div>

              {/* Insurance */}
              <div className="info-row">
                <span className="info-label">Insurance</span>
                <span className="info-value" style={{ color: statusColor(data.insurance?.status) }}>
                  {data.insurance?.status === 'VALID' && <CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />}
                  {data.insurance?.status === 'EXPIRED' && <XCircle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />}
                  {data.insurance?.status || 'NOT FOUND'}
                  {data.insurance?.valid_until && ` (until ${data.insurance.valid_until})`}
                  {data.insurance?.type && ` - ${data.insurance.type}`}
                </span>
              </div>

              {/* Stolen */}
              <div className="info-row">
                <span className="info-label">Stolen Vehicle</span>
                <span
                  className="info-value"
                  style={{
                    color: data.is_stolen ? 'var(--color-danger)' : 'var(--color-success)',
                    fontWeight: 700,
                  }}
                >
                  {data.is_stolen ? (
                    <><AlertTriangle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} /> YES - REPORTED STOLEN</>
                  ) : (
                    <><CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} /> NO</>
                  )}
                </span>
              </div>

              {/* Offender Level */}
              <div className="info-row">
                <span className="info-label">Offender Level</span>
                <span className="info-value">
                  <div className="offender-level">
                    <div className="offender-level-dots">
                      {offenderDots(data.offender_level)}
                    </div>
                    <span style={{ fontWeight: 700 }}>
                      Level {data.offender_level}
                    </span>
                  </div>
                </span>
              </div>

              {/* Total Violations */}
              <div className="info-row">
                <span className="info-label">Total Violations</span>
                <span className="info-value" style={{ fontSize: '1.25rem', fontWeight: 800 }}>
                  {data.total_violations}
                </span>
              </div>

              {/* Court Summons (offender level >= 3) */}
              {data.offender_level >= 3 && (
                <button
                  className="btn btn-danger mt-4"
                  style={{ width: '100%', justifyContent: 'center' }}
                  onClick={() => api.generateReport(plate).catch(console.error)}
                >
                  <FileText size={16} />
                  Generate Court Summons PDF
                </button>
              )}
            </div>
          </div>

          {/* ── Violation History Table ── */}
          {data.violation_history && data.violation_history.length > 0 && (
            <div className="card card-body">
              <h3 className="mb-4">
                <AlertTriangle size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                Violation History ({data.total_violations} records)
              </h3>
              <div className="data-table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Violations</th>
                      <th>Score</th>
                      <th>Level</th>
                      <th>Zone</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.violation_history.map((v, i) => (
                      <tr key={i}>
                        <td>
                          {v.timestamp
                            ? new Date(v.timestamp).toLocaleString()
                            : '\u2014'}
                        </td>
                        <td>
                          {v.violation_types
                            ? v.violation_types
                                .split(',')
                                .map((t) => cleanViolation(t.trim()))
                                .join(', ')
                            : '\u2014'}
                        </td>
                        <td className="score-cell" style={{
                          color: v.risk_score > 60
                            ? 'var(--color-critical)'
                            : v.risk_score > 40
                              ? 'var(--color-warning)'
                              : 'var(--color-success)',
                        }}>
                          {v.risk_score}
                        </td>
                        <td>
                          <StatusBadge level={v.alert_level} />
                        </td>
                        <td>{v.zone_id || '\u2014'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
