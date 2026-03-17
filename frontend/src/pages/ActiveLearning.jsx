import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';

export default function ActiveLearning() {
  const [stats, setStats] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [retrainResult, setRetrainResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getFeedbackStats().catch(() => ({ total_feedback: 0, entries: [] })),
      api.getModelInfo().catch(() => null),
    ]).then(([statsData, modelData]) => {
      setStats(statsData);
      setModelInfo(modelData);
    }).finally(() => setLoading(false));
  }, []);

  const handleRetrain = useCallback(async () => {
    setRetraining(true);
    setError('');
    setRetrainResult(null);
    try {
      const res = await api.triggerRetrain();
      setRetrainResult(res);
      // Refresh model info after retrain
      const info = await api.getModelInfo().catch(() => null);
      if (info) setModelInfo(info);
    } catch (err) {
      setError(err.message || 'Retraining failed');
    } finally {
      setRetraining(false);
    }
  }, []);

  if (loading) return <div className="loading"><div className="spinner"></div>Loading feedback data...</div>;

  const feedbackCount = stats?.total_feedback || 0;
  const minSamples = modelInfo?.min_training_samples || 10;
  const readyForTraining = modelInfo?.ready_for_training || feedbackCount >= minSamples;
  const modelVersion = modelInfo?.model_version || 'v1.0';

  return (
    <div className="page">
      <div className="page-header">
        <h2>Active Learning</h2>
        <p>Model learns from your corrections — view feedback and trigger retraining</p>
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

      {/* Retrain Button */}
      <div className="card" style={{ marginBottom: 24, textAlign: 'center', padding: 30 }}>
        <h3 style={{ marginBottom: 8 }}>Retrain Pipeline</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: 20, fontSize: 13 }}>
          Use corrections collected from Image Verify to fine-tune the detection model.
          {!readyForTraining && ` Minimum ${minSamples} corrections required.`}
        </p>
        <button
          className="btn btn-primary"
          onClick={handleRetrain}
          disabled={retraining || !readyForTraining}
          style={{ fontSize: 16, padding: '14px 40px' }}
        >
          {retraining ? 'Retraining Model...' : 'Start Retraining'}
        </button>
        {!readyForTraining && (
          <p style={{ color: 'var(--text-muted)', marginTop: 10, fontSize: 12 }}>
            Submit {minSamples - feedbackCount} more correction(s) via Image Verify page
          </p>
        )}
      </div>

      {error && (
        <div className="card" style={{ borderColor: '#ef4444', color: '#fca5a5', marginBottom: 20, padding: 16 }}>
          {error}
        </div>
      )}

      {/* Retrain Pipeline Visualization */}
      {retrainResult && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-title">Retraining Pipeline</div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 16, fontSize: 13 }}>
            {retrainResult.message}
          </p>

          {/* Metrics summary */}
          {retrainResult.metrics && (
            <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
              <div style={{ padding: '10px 16px', borderRadius: 8, background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.2)' }}>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>Loss</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#22c55e' }}>{retrainResult.metrics.final_loss}</div>
              </div>
              <div style={{ padding: '10px 16px', borderRadius: 8, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)' }}>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>Accuracy</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#818cf8' }}>{(retrainResult.metrics.accuracy * 100).toFixed(1)}%</div>
              </div>
              <div style={{ padding: '10px 16px', borderRadius: 8, background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>mAP50</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#f59e0b' }}>{(retrainResult.metrics.mAP50 * 100).toFixed(1)}%</div>
              </div>
              <div style={{ padding: '10px 16px', borderRadius: 8, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)' }}>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>Epochs</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#818cf8' }}>{retrainResult.metrics.epochs}</div>
              </div>
            </div>
          )}

          {(retrainResult.pipeline || []).map((step) => (
            <div key={step.step} style={{
              display: 'flex', alignItems: 'center', gap: 14, padding: '12px 16px',
              marginBottom: 4, borderRadius: 8,
              background: step.status === 'completed'
                ? 'rgba(34,197,94,0.1)' : step.status === 'pending'
                ? 'rgba(245,158,11,0.1)' : 'rgba(99,102,241,0.1)',
              borderLeft: step.status === 'completed'
                ? '3px solid rgba(34,197,94,0.5)' : step.status === 'pending'
                ? '3px solid rgba(245,158,11,0.5)' : '3px solid rgba(99,102,241,0.5)',
            }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%', display: 'flex',
                alignItems: 'center', justifyContent: 'center', fontWeight: 800,
                background: step.status === 'completed' ? '#22c55e' : step.status === 'pending' ? '#f59e0b' : '#6366f1',
                color: 'white', fontSize: 13, flexShrink: 0,
              }}>
                {step.status === 'completed' ? '\u2713' : step.step}
              </div>
              <div style={{ flex: 1 }}>
                <span style={{ fontWeight: 600 }}>{step.name}</span>
                {step.detail && (
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{step.detail}</div>
                )}
              </div>
              <span style={{
                fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 12,
                background: step.status === 'completed'
                  ? 'rgba(34,197,94,0.15)' : step.status === 'pending'
                  ? 'rgba(245,158,11,0.15)' : 'rgba(99,102,241,0.15)',
                color: step.status === 'completed' ? '#86efac' : step.status === 'pending' ? '#fcd34d' : '#a5b4fc',
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
