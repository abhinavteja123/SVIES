import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import { Settings, CheckCircle, AlertCircle, Cpu, Shield, Camera, Clock } from 'lucide-react';

const CATEGORY_ICONS = {
  vehicle: Cpu,
  helmet: Shield,
  plate: Camera,
  age: Clock,
};

const CATEGORY_COLORS = {
  vehicle: { bg: 'rgba(99,102,241,0.08)', border: 'rgba(99,102,241,0.25)', text: '#818cf8', badge: '#6366f1' },
  helmet: { bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.25)', text: '#fbbf24', badge: '#f59e0b' },
  plate: { bg: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.25)', text: '#4ade80', badge: '#22c55e' },
  age: { bg: 'rgba(168,85,247,0.08)', border: 'rgba(168,85,247,0.25)', text: '#c084fc', badge: '#a855f7' },
};

export default function ActiveLearning() {
  const [stats, setStats] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [retrainResult, setRetrainResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [error, setError] = useState('');
  const [switching, setSwitching] = useState('');
  const [switchMsg, setSwitchMsg] = useState('');

  const fetchData = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.getFeedbackStats().catch(() => ({ total_feedback: 0, entries: [] })),
      api.getModelInfo().catch(() => null),
    ]).then(([statsData, modelData]) => {
      setStats(statsData);
      setModelInfo(modelData);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleRetrain = useCallback(async () => {
    setRetraining(true);
    setError('');
    setRetrainResult(null);
    try {
      const res = await api.triggerRetrain();
      setRetrainResult(res);
      fetchData();
    } catch (err) {
      setError(err.message || 'Retraining failed');
    } finally {
      setRetraining(false);
    }
  }, [fetchData]);

  const handleSetActiveModel = useCallback(async (category, modelName) => {
    setSwitching(`${category}:${modelName}`);
    setSwitchMsg('');
    setError('');
    try {
      const res = await api.setActiveModel(category, modelName);
      setSwitchMsg(res.message || `Switched to ${modelName}`);
      fetchData();
    } catch (err) {
      setError(err.message || 'Failed to switch model');
    } finally {
      setSwitching('');
    }
  }, [fetchData]);

  if (loading) return <div className="loading"><div className="spinner"></div>Loading feedback data...</div>;

  const feedbackCount = stats?.total_feedback || 0;
  const minSamples = modelInfo?.min_training_samples || 10;
  const readyForTraining = modelInfo?.ready_for_training || feedbackCount >= minSamples;
  const modelVersion = modelInfo?.model_version || 'v1.0';
  const activeModels = modelInfo?.active_models || {};
  const modelsByCategory = modelInfo?.models_by_category || {};
  const categories = modelInfo?.categories || {};

  return (
    <div className="page">
      <div className="page-header">
        <h2>Active Learning</h2>
        <p>Manage SVIES detection models — view feedback, switch model versions, and trigger retraining</p>
      </div>

      {/* Stats */}
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 24 }}>
        <div className="kpi-card accent">
          <div className="kpi-label">Total Corrections</div>
          <div className="kpi-value">{feedbackCount}</div>
        </div>
        <div className="kpi-card success">
          <div className="kpi-label">Ready for Training</div>
          <div className="kpi-value" style={{ color: readyForTraining ? '#22c55e' : '#f59e0b' }}>
            {readyForTraining ? 'Yes' : `${feedbackCount}/${minSamples}`}
          </div>
        </div>
        <div className="kpi-card warning">
          <div className="kpi-label">Model Version</div>
          <div className="kpi-value" style={{ fontSize: 20 }}>{modelVersion}</div>
        </div>
        <div className="kpi-card" style={{ borderColor: modelInfo?.status === 'ready' ? 'rgba(34,197,94,0.3)' : 'rgba(99,102,241,0.3)' }}>
          <div className="kpi-label">Status</div>
          <div className="kpi-value" style={{ fontSize: 16, color: modelInfo?.status === 'ready' ? '#22c55e' : '#6366f1' }}>
            {modelInfo?.status === 'ready' ? 'Ready to Train' : 'Collecting Data'}
          </div>
        </div>
      </div>

      {/* ═══════════ Model Version Selector (4 Categories) ═══════════ */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <Settings size={18} />
          Model Version Management
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 16 }}>
          SVIES uses 4 detection models: Vehicle Classifier (YOLO), Helmet Detector (YOLO),
          Plate Detector (YOLO), and Age Classifier (ResNet50). Select which version of each model
          to use. Retrained models are saved as versioned files (v1, v2, v3…).
        </p>

        {switchMsg && (
          <div style={{
            padding: '10px 16px', borderRadius: 8, marginBottom: 16,
            background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <CheckCircle size={16} color="#22c55e" />
            <span style={{ color: '#4ade80', fontSize: 13 }}>{switchMsg}</span>
          </div>
        )}

        {/* 4 Category Sections */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {Object.entries(_MODEL_CATEGORIES_ORDER).map(([cat, _]) => {
            const catLabel = categories[cat] || cat;
            const catModels = modelsByCategory[cat] || [];
            const activeName = activeModels[cat] || 'unknown';
            const colors = CATEGORY_COLORS[cat] || CATEGORY_COLORS.vehicle;
            const Icon = CATEGORY_ICONS[cat] || Cpu;

            return (
              <div key={cat} style={{
                border: `1px solid ${colors.border}`,
                borderRadius: 12,
                overflow: 'hidden',
                background: colors.bg,
              }}>
                {/* Category header */}
                <div style={{
                  padding: '12px 18px',
                  display: 'flex', alignItems: 'center', gap: 10,
                  borderBottom: `1px solid ${colors.border}`,
                }}>
                  <Icon size={20} color={colors.text} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>{catLabel}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      Active: <code style={{ color: colors.text }}>{activeName}</code>
                      {cat === 'age' && <span style={{ marginLeft: 8, fontSize: 10, opacity: 0.7 }}>(ResNet50-based)</span>}
                    </div>
                  </div>
                  <span style={{
                    padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700,
                    background: `${colors.badge}22`, color: colors.badge, border: `1px solid ${colors.badge}44`,
                  }}>
                    {catModels.length} version{catModels.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {/* Model list */}
                {catModels.length > 0 ? (
                  <div style={{ padding: '4px 0' }}>
                    {catModels.map((m) => (
                      <div key={m.name} style={{
                        display: 'flex', alignItems: 'center', gap: 12,
                        padding: '8px 18px',
                        background: m.is_active ? `${colors.badge}0a` : 'transparent',
                        borderLeft: m.is_active ? `3px solid ${colors.badge}` : '3px solid transparent',
                      }}>
                        <div style={{ flex: 1 }}>
                          <span style={{ fontFamily: 'monospace', fontWeight: 600, fontSize: 13 }}>{m.name}</span>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 10 }}>
                            {m.size_mb} MB · {new Date(m.modified).toLocaleDateString()}
                          </span>
                        </div>
                        {m.is_active ? (
                          <span style={{
                            padding: '2px 10px', borderRadius: 12, fontSize: 10, fontWeight: 700,
                            background: '#22c55e22', color: '#22c55e', border: '1px solid #22c55e44',
                          }}>
                            ● ACTIVE
                          </span>
                        ) : (
                          <button
                            className="btn btn-secondary"
                            disabled={switching === `${cat}:${m.name}`}
                            onClick={() => handleSetActiveModel(cat, m.name)}
                            style={{
                              fontSize: 11, padding: '3px 12px', borderRadius: 8,
                              minWidth: 90,
                            }}
                          >
                            {switching === `${cat}:${m.name}` ? 'Switching…' : 'Set Active'}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: '14px 18px', color: 'var(--text-muted)', fontSize: 12 }}>
                    No model files for this category
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Retrain Button */}
      <div className="card" style={{ marginBottom: 24, textAlign: 'center', padding: 30 }}>
        <h3 style={{ marginBottom: 8 }}>Retrain Pipeline</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: 12, fontSize: 13 }}>
          Fine-tune with corrections collected from Image Verify.
          {!readyForTraining && ` Minimum ${minSamples} corrections required.`}
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginBottom: 16, flexWrap: 'wrap' }}>
          {Object.entries(categories).map(([cat, label]) => {
            const colors = CATEGORY_COLORS[cat] || CATEGORY_COLORS.vehicle;
            return (
              <div key={cat} style={{
                padding: '6px 14px', borderRadius: 8, fontSize: 12,
                background: colors.bg, border: `1px solid ${colors.border}`,
              }}>
                <span style={{ color: 'var(--text-muted)' }}>{label}: </span>
                <code style={{ color: colors.text, fontWeight: 600 }}>{activeModels[cat] || 'default'}</code>
              </div>
            );
          })}
        </div>
        <button
          className="btn btn-primary"
          onClick={handleRetrain}
          disabled={retraining || !readyForTraining}
          style={{ fontSize: 16, padding: '14px 40px' }}
        >
          {retraining ? 'Retraining Model…' : 'Start Retraining'}
        </button>
        {!readyForTraining && (
          <p style={{ color: 'var(--text-muted)', marginTop: 10, fontSize: 12 }}>
            Submit {minSamples - feedbackCount} more correction(s) via Image Verify page
          </p>
        )}
      </div>

      {error && (
        <div className="card" style={{ borderColor: '#ef4444', color: '#fca5a5', marginBottom: 20, padding: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
          <AlertCircle size={18} /> {error}
        </div>
      )}

      {/* Retrain Pipeline Visualization */}
      {retrainResult && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-title">Retraining Pipeline</div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 16, fontSize: 13 }}>
            {retrainResult.message}
          </p>

          {retrainResult.metrics && (
            <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
              {[
                { label: 'Loss', value: retrainResult.metrics.final_loss, color: '#22c55e', bg: 'rgba(34,197,94,0.1)', border: 'rgba(34,197,94,0.2)' },
                { label: 'Accuracy', value: `${(retrainResult.metrics.accuracy * 100).toFixed(1)}%`, color: '#818cf8', bg: 'rgba(99,102,241,0.1)', border: 'rgba(99,102,241,0.2)' },
                { label: 'mAP50', value: `${(retrainResult.metrics.mAP50 * 100).toFixed(1)}%`, color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.2)' },
                { label: 'Epochs', value: retrainResult.metrics.epochs, color: '#818cf8', bg: 'rgba(99,102,241,0.1)', border: 'rgba(99,102,241,0.2)' },
              ].map((m) => (
                <div key={m.label} style={{ padding: '10px 16px', borderRadius: 8, background: m.bg, border: `1px solid ${m.border}` }}>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>{m.label}</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: m.color }}>{m.value}</div>
                </div>
              ))}
            </div>
          )}

          {(retrainResult.pipeline || []).map((step) => (
            <div key={step.step} style={{
              display: 'flex', alignItems: 'center', gap: 14, padding: '12px 16px',
              marginBottom: 4, borderRadius: 8,
              background: step.status === 'completed' ? 'rgba(34,197,94,0.1)'
                : step.status === 'failed' ? 'rgba(239,68,68,0.1)'
                : step.status === 'pending' ? 'rgba(245,158,11,0.1)' : 'rgba(99,102,241,0.1)',
              borderLeft: step.status === 'completed' ? '3px solid rgba(34,197,94,0.5)'
                : step.status === 'failed' ? '3px solid rgba(239,68,68,0.5)'
                : step.status === 'pending' ? '3px solid rgba(245,158,11,0.5)' : '3px solid rgba(99,102,241,0.5)',
            }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%', display: 'flex',
                alignItems: 'center', justifyContent: 'center', fontWeight: 800,
                background: step.status === 'completed' ? '#22c55e' : step.status === 'failed' ? '#ef4444' : step.status === 'pending' ? '#f59e0b' : '#6366f1',
                color: 'white', fontSize: 13, flexShrink: 0,
              }}>
                {step.status === 'completed' ? '\u2713' : step.status === 'failed' ? '\u2717' : step.step}
              </div>
              <div style={{ flex: 1 }}>
                <span style={{ fontWeight: 600 }}>{step.name}</span>
                {step.detail && <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{step.detail}</div>}
              </div>
              <span style={{
                fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 12,
                background: step.status === 'completed' ? 'rgba(34,197,94,0.15)'
                  : step.status === 'failed' ? 'rgba(239,68,68,0.15)'
                  : step.status === 'pending' ? 'rgba(245,158,11,0.15)' : 'rgba(99,102,241,0.15)',
                color: step.status === 'completed' ? '#86efac' : step.status === 'failed' ? '#fca5a5' : step.status === 'pending' ? '#fcd34d' : '#a5b4fc',
              }}>
                {step.status.toUpperCase()}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Feedback History */}
      {stats?.entries && stats.entries.length > 0 && (
        <div className="card">
          <div className="card-title">Recent Corrections</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th><th>Original Plate</th><th>Corrected Plate</th>
                <th>Vehicle Type</th><th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {stats.entries.slice().reverse().map((e, i) => (
                <tr key={i}>
                  <td style={{ fontSize: 12 }}>{e.timestamp}</td>
                  <td style={{ fontFamily: 'monospace' }}>{e.original_plate || '\u2014'}</td>
                  <td style={{ fontFamily: 'monospace', color: '#22c55e' }}>
                    {e.correct_plate || '\u2014'}
                  </td>
                  <td>{e.correct_vehicle_type || '\u2014'}</td>
                  <td style={{ fontSize: 12, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {e.notes || '\u2014'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Category rendering order — matches backend _MODEL_CATEGORIES
const _MODEL_CATEGORIES_ORDER = {
  vehicle: 'Vehicle Detector',
  helmet: 'Helmet Detector',
  plate: 'Plate Detector',
  age: 'Age Classifier (ResNet50)',
};
