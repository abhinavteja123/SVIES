import { useState, useEffect, useRef } from 'react';
import { AlertTriangle, Search, Download, X } from 'lucide-react';
import { api, API_BASE } from '../api';
import { StatusBadge, LoadingSpinner, EmptyState } from '../components';

export default function Violations() {
  const [data, setData] = useState({
    violations: [],
    total: 0,
    page: 1,
    total_pages: 0,
  });
  const [filters, setFilters] = useState({
    level: '',
    plate: '',
    days: 30,
    page: 1,
  });
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [selectedViolation, setSelectedViolation] = useState(null);
  const debounceRef = useRef(null);

  /* ── Fetch violations from API ── */
  const fetchData = () => {
    setLoading(true);
    const params = { days: filters.days, page: filters.page, per_page: 25 };
    if (filters.level) params.level = filters.level;
    if (filters.plate) params.plate = filters.plate;

    api
      .getViolations(params)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  /* Auto-fetch when non-text filters change immediately */
  useEffect(fetchData, [filters.level, filters.days, filters.page]);

  /* Debounce plate text input (500ms) */
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(fetchData, 500);
    return () => clearTimeout(debounceRef.current);
  }, [filters.plate]);

  /* Manual search resets to page 1 */
  const handleSearch = (e) => {
    e.preventDefault();
    setFilters((f) => ({ ...f, page: 1 }));
  };

  const handleExport = async (format) => {
    setExporting(true);
    try {
      const params = { days: filters.days };
      if (filters.level) params.level = filters.level;
      if (filters.plate) params.plate = filters.plate;
      await api.exportViolations(params, format);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  /* ── Helpers ── */
  const cleanViolation = (v) =>
    v.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  const scoreClass = (score) => {
    if (score > 60) return 'score-critical';
    if (score > 40) return 'score-high';
    if (score > 20) return 'score-medium';
    return 'score-low';
  };

  const getImageUrl = (path) => {
    if (!path) return null;
    if (path.startsWith('http')) return path;
    return `${API_BASE}${path}`;
  };

  const rangeStart = (data.page - 1) * 25 + 1;
  const rangeEnd = Math.min(data.page * 25, data.total);

  /* ═══════════════════════ Render ═══════════════════════ */
  return (
    <div className="page">
      {/* ── Header ── */}
      <div className="page-header">
        <h2>Violation Log</h2>
        <p>Complete enforcement record with filtering</p>
      </div>

      {/* ── Filter bar ── */}
      <form className="filter-bar" onSubmit={handleSearch}>
        <div className="form-group">
          <input
            className="form-input form-input-mono"
            placeholder="Search plate number..."
            value={filters.plate}
            onChange={(e) => setFilters((f) => ({ ...f, plate: e.target.value }))}
          />
        </div>

        <div className="form-group">
          <select
            className="form-select"
            value={filters.level}
            onChange={(e) =>
              setFilters((f) => ({ ...f, level: e.target.value, page: 1 }))
            }
          >
            <option value="">All Levels</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        <div className="form-group">
          <select
            className="form-select"
            value={filters.days}
            onChange={(e) =>
              setFilters((f) => ({ ...f, days: +e.target.value, page: 1 }))
            }
          >
            <option value={7}>Last 7 Days</option>
            <option value={30}>Last 30 Days</option>
            <option value={90}>Last 90 Days</option>
          </select>
        </div>

        <button type="submit" className="btn btn-primary">
          <Search size={16} />
          Search
        </button>

        <button type="button" className="btn btn-secondary" disabled={exporting}
          onClick={() => handleExport('csv')}>
          <Download size={16} />
          CSV
        </button>
        <button type="button" className="btn btn-secondary" disabled={exporting}
          onClick={() => handleExport('pdf')}>
          <Download size={16} />
          PDF
        </button>
      </form>

      {/* ── Data area ── */}
      <div className="card card-body">
        {loading ? (
          <LoadingSpinner message="Loading violations..." />
        ) : data.violations.length === 0 ? (
          <EmptyState
            icon={<AlertTriangle size={28} />}
            title="No violations found"
            text="Adjust filters or run the detection pipeline"
          />
        ) : (
          <>
            {/* ── Table ── */}
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Evidence</th>
                    <th>Plate</th>
                    <th>Timestamp</th>
                    <th>Vehicle</th>
                    <th>Violations</th>
                    <th>Risk Score</th>
                    <th>Level</th>
                    <th>Zone</th>
                  </tr>
                </thead>
                <tbody>
                  {data.violations.map((v, i) => {
                    const capturedUrl = getImageUrl(v.captured_image);
                    const annotatedUrl = getImageUrl(v.annotated_image);
                    const hasImages = capturedUrl || annotatedUrl;
                    return (
                      <tr key={i} style={{ cursor: hasImages ? 'pointer' : 'default' }}
                        onClick={() => hasImages && setSelectedViolation(v)}>
                        <td>
                          {annotatedUrl ? (
                            <img
                              src={annotatedUrl}
                              alt="Detection"
                              style={{
                                width: 80,
                                height: 50,
                                objectFit: 'cover',
                                borderRadius: 4,
                                border: '1px solid var(--border-default)',
                              }}
                              onError={(e) => { e.target.style.display = 'none'; }}
                            />
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>No image</span>
                          )}
                        </td>
                        <td className="plate-cell">{v.plate}</td>
                        <td>
                          {v.timestamp
                            ? new Date(v.timestamp).toLocaleString()
                            : '\u2014'}
                        </td>
                        <td>
                          <span style={{
                            display: 'inline-block',
                            padding: '2px 8px',
                            borderRadius: 12,
                            fontSize: 11,
                            fontWeight: 600,
                            background: 'rgba(59,130,246,0.12)',
                            color: '#60a5fa',
                          }}>
                            {v.vehicle_type || '\u2014'}
                          </span>
                          {v.owner_name && (
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                              {v.owner_name}
                            </div>
                          )}
                        </td>
                        <td>
                          {v.violation_types
                            ? v.violation_types
                                .split(',')
                                .map((t) => cleanViolation(t.trim()))
                                .join(', ')
                            : '\u2014'}
                        </td>
                        <td className={`score-cell ${scoreClass(v.risk_score)}`}>
                          {v.risk_score}
                        </td>
                        <td>
                          <StatusBadge level={v.alert_level} />
                        </td>
                        <td>{v.zone_id || '\u2014'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* ── Pagination ── */}
            <div className="pagination">
              <span>
                Showing {rangeStart}-{rangeEnd} of {data.total} results
              </span>
              <div className="pagination-buttons">
                <button
                  className="btn btn-secondary btn-sm"
                  disabled={data.page <= 1}
                  onClick={() =>
                    setFilters((f) => ({ ...f, page: f.page - 1 }))
                  }
                >
                  Previous
                </button>
                <span className="form-label" style={{ padding: '6px 12px' }}>
                  Page {data.page} of {data.total_pages}
                </span>
                <button
                  className="btn btn-secondary btn-sm"
                  disabled={data.page >= data.total_pages}
                  onClick={() =>
                    setFilters((f) => ({ ...f, page: f.page + 1 }))
                  }
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ═══════════ Violation Detail Modal ═══════════ */}
      {selectedViolation && (
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            background: 'rgba(0,0,0,0.75)', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            padding: 20,
          }}
          onClick={() => setSelectedViolation(null)}
        >
          <div
            className="card"
            style={{
              maxWidth: 900, width: '100%', maxHeight: '90vh',
              overflowY: 'auto', position: 'relative',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              onClick={() => setSelectedViolation(null)}
              style={{
                position: 'absolute', top: 12, right: 12,
                background: 'rgba(255,255,255,0.1)', border: 'none',
                borderRadius: '50%', width: 32, height: 32,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: 'var(--text-secondary)',
              }}
            >
              <X size={18} />
            </button>

            {/* Title */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <span style={{
                  fontFamily: 'monospace', fontSize: 20, fontWeight: 800,
                  letterSpacing: 2, color: 'var(--text-accent)',
                  background: 'var(--bg-secondary)', padding: '4px 14px',
                  borderRadius: 8,
                }}>
                  {selectedViolation.plate}
                </span>
                <StatusBadge level={selectedViolation.alert_level} />
                {selectedViolation.vehicle_type && (
                  <span style={{
                    padding: '2px 10px', borderRadius: 12, fontSize: 12,
                    fontWeight: 600, background: 'rgba(59,130,246,0.12)',
                    color: '#60a5fa',
                  }}>
                    {selectedViolation.vehicle_type}
                  </span>
                )}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                {selectedViolation.timestamp
                  ? new Date(selectedViolation.timestamp).toLocaleString()
                  : '\u2014'}
                {selectedViolation.owner_name && (
                  <span> | Owner: <strong>{selectedViolation.owner_name}</strong></span>
                )}
                {selectedViolation.model_used && (
                  <span> | Model: <strong>{selectedViolation.model_used}</strong></span>
                )}
              </div>
            </div>

            {/* Images side by side */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
              {/* Captured (input) image */}
              <div>
                <div style={{
                  fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)',
                  marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1,
                }}>
                  Captured Photo (Input)
                </div>
                {getImageUrl(selectedViolation.captured_image) ? (
                  <img
                    src={getImageUrl(selectedViolation.captured_image)}
                    alt="Captured"
                    style={{
                      width: '100%', borderRadius: 8,
                      border: '1px solid var(--border-default)',
                    }}
                    onError={(e) => { e.target.parentNode.innerHTML = '<div style="padding:40px;text-align:center;color:#64748b">Image unavailable</div>'; }}
                  />
                ) : (
                  <div style={{
                    padding: 40, textAlign: 'center', color: 'var(--text-muted)',
                    background: 'var(--bg-secondary)', borderRadius: 8,
                  }}>
                    No captured image
                  </div>
                )}
              </div>

              {/* Annotated (model output) image */}
              <div>
                <div style={{
                  fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)',
                  marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1,
                }}>
                  Model Output (Annotated)
                </div>
                {getImageUrl(selectedViolation.annotated_image) ? (
                  <img
                    src={getImageUrl(selectedViolation.annotated_image)}
                    alt="Annotated"
                    style={{
                      width: '100%', borderRadius: 8,
                      border: '1px solid var(--border-default)',
                    }}
                    onError={(e) => { e.target.parentNode.innerHTML = '<div style="padding:40px;text-align:center;color:#64748b">Image unavailable</div>'; }}
                  />
                ) : (
                  <div style={{
                    padding: 40, textAlign: 'center', color: 'var(--text-muted)',
                    background: 'var(--bg-secondary)', borderRadius: 8,
                  }}>
                    No annotated image
                  </div>
                )}
              </div>
            </div>

            {/* Details grid */}
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 12,
            }}>
              <div style={{
                padding: '12px 14px', borderRadius: 8,
                background: 'var(--bg-secondary)', border: '1px solid var(--border-default)',
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Risk Score</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)' }}>
                  {selectedViolation.risk_score}
                </div>
              </div>
              <div style={{
                padding: '12px 14px', borderRadius: 8,
                background: 'var(--bg-secondary)', border: '1px solid var(--border-default)',
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Zone</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {selectedViolation.zone_id || 'None'}
                </div>
              </div>
              <div style={{
                padding: '12px 14px', borderRadius: 8,
                background: 'var(--bg-secondary)', border: '1px solid var(--border-default)',
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Detection Model</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {selectedViolation.model_used || 'N/A'}
                </div>
              </div>
              <div style={{
                padding: '12px 14px', borderRadius: 8,
                background: 'var(--bg-secondary)', border: '1px solid var(--border-default)',
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Vehicle Type</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {selectedViolation.vehicle_type || 'N/A'}
                </div>
              </div>
            </div>

            {/* Violations list */}
            {selectedViolation.violation_types && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  Violations
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {selectedViolation.violation_types.split(',').map((v, i) => (
                    <span key={i} style={{
                      padding: '4px 12px', borderRadius: 16, fontSize: 12, fontWeight: 600,
                      background: 'rgba(239,68,68,0.12)', color: '#fca5a5',
                      border: '1px solid rgba(239,68,68,0.25)',
                    }}>
                      {cleanViolation(v.trim())}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
