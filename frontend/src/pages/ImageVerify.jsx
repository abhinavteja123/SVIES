import { useState, useRef, useCallback } from 'react';
import { api } from '../api';
import { ImagePlus } from 'lucide-react';

const STEP_STYLES = {
  completed: { bg: 'rgba(34,197,94,0.1)', border: 'rgba(34,197,94,0.3)', dot: '#22c55e' },
  danger: { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', dot: '#ef4444' },
  warning: { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)', dot: '#f59e0b' },
  skipped: { bg: 'rgba(100,116,139,0.1)', border: 'rgba(100,116,139,0.3)', dot: '#64748b' },
  low: { bg: 'rgba(34,197,94,0.1)', border: 'rgba(34,197,94,0.3)', dot: '#22c55e' },
  medium: { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)', dot: '#f59e0b' },
};

function PipelineStep({ step, index }) {
  const style = STEP_STYLES[step.status] || STEP_STYLES.completed;

  // Determine verification badge for OCR step
  const isOCRStep = step.name && step.name.includes('OCR');
  const verifiedBy = step.verified_by;

  const VERIFY_BADGE = {
    groq_verified: { label: 'Groq Verified', bg: 'rgba(34,197,94,0.18)', color: '#4ade80', icon: '✅' },
    groq_corrected: { label: 'Groq Corrected', bg: 'rgba(59,130,246,0.18)', color: '#60a5fa', icon: '🤖' },
    easyocr: { label: 'EasyOCR Only', bg: 'rgba(245,158,11,0.15)', color: '#fbbf24', icon: '🔤' },
    none: { label: 'No OCR', bg: 'rgba(100,116,139,0.15)', color: '#94a3b8', icon: '—' },
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 14,
      padding: '14px 16px', marginBottom: 2,
      borderRadius: 8,
      background: style.bg,
      borderLeft: `3px solid ${style.border}`,
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 16, flexShrink: 0,
        background: 'var(--bg-secondary)',
        border: `2px solid ${style.dot}`,
      }}>
        {step.icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
          {step.name}
          {/* Groq vs OCR badge */}
          {isOCRStep && verifiedBy && VERIFY_BADGE[verifiedBy] && (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              padding: '2px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700,
              background: VERIFY_BADGE[verifiedBy].bg,
              color: VERIFY_BADGE[verifiedBy].color,
              border: `1px solid ${VERIFY_BADGE[verifiedBy].color}33`,
            }}>
              {VERIFY_BADGE[verifiedBy].icon} {VERIFY_BADGE[verifiedBy].label}
            </span>
          )}
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{step.detail}</div>
        {/* Show raw OCR text vs final output for OCR step */}
        {isOCRStep && step.raw_text && verifiedBy === 'groq_corrected' && (
          <div style={{
            marginTop: 6, padding: '6px 10px', borderRadius: 6,
            background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)',
            fontSize: 12, fontFamily: 'monospace',
          }}>
            <span style={{ color: '#94a3b8' }}>EasyOCR: </span>
            <span style={{ color: '#f87171', textDecoration: 'line-through' }}>{step.raw_text}</span>
            <span style={{ color: '#94a3b8', margin: '0 6px' }}>&rarr;</span>
            <span style={{ color: '#4ade80', fontWeight: 700 }}>Groq AI: {step.detail?.match(/Plate: (\S+)/)?.[1] || '—'}</span>
          </div>
        )}
        {isOCRStep && verifiedBy === 'groq_verified' && (
          <div style={{
            marginTop: 6, padding: '4px 10px', borderRadius: 6,
            background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)',
            fontSize: 12,
          }}>
            <span style={{ color: '#4ade80' }}>Both EasyOCR and Groq AI agree on this plate number</span>
          </div>
        )}
        {step.flags && step.flags.length > 0 && (
          <div style={{ marginTop: 6 }}>
            {step.flags.map((f, i) => (
              <span key={i} style={{
                display: 'inline-block', marginRight: 6, marginBottom: 4,
                padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600,
                background: 'rgba(239,68,68,0.15)', color: '#fca5a5',
                border: '1px solid rgba(239,68,68,0.3)',
              }}>🚩 {f}</span>
            ))}
          </div>
        )}
        {step.violations && step.violations.length > 0 && (
          <div style={{ marginTop: 6 }}>
            {step.violations.map((v, i) => (
              <span key={i} style={{
                display: 'inline-block', marginRight: 6, marginBottom: 4,
                padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600,
                background: 'rgba(239,68,68,0.15)', color: '#fca5a5',
                border: '1px solid rgba(239,68,68,0.3)',
              }}>⚠️ {v}</span>
            ))}
          </div>
        )}
        {step.breakdown && (
          <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text-muted)' }}>
            {Object.entries(step.breakdown).map(([k, v]) => (
              <span key={k} style={{ marginRight: 12 }}>{k}: +{v}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ImageVerify() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [feedbackOpen, setFeedbackOpen] = useState(null);
  const [feedbackData, setFeedbackData] = useState({ correctPlate: '', correctVehicleType: '', notes: '' });
  const [feedbackSentFor, setFeedbackSentFor] = useState(new Set());
  const [fullFeedbackOpen, setFullFeedbackOpen] = useState(false);
  const [fullFeedbackData, setFullFeedbackData] = useState({ accuracyRating: 0, missedVehicles: 0, falseDetections: 0, notes: '' });
  const [fullFeedbackSent, setFullFeedbackSent] = useState(false);
  const fileRef = useRef(null);

  const handleFile = useCallback((f) => {
    if (!f || !f.type.startsWith('image/')) return;
    setFile(f);
    setResult(null);
    setError('');
    setFeedbackSentFor(new Set());
    setFullFeedbackSent(false);
    setFullFeedbackOpen(false);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  }, []);

  const handleUpload = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await api.processImage(file);
      setResult(res);
    } catch (err) {
      setError(err.message || 'Failed to process image');
    } finally {
      setLoading(false);
    }
  }, [file]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    handleFile(e.dataTransfer.files[0]);
  }, [handleFile]);

  const handleFeedback = useCallback(async (vehicleIdx) => {
    try {
      await api.submitFeedback({
        file,
        plate: result?.pipeline_results?.[vehicleIdx]?.plate || '',
        correctPlate: feedbackData.correctPlate,
        correctVehicleType: feedbackData.correctVehicleType,
        notes: feedbackData.notes,
      });
      setFeedbackSentFor(prev => new Set([...prev, vehicleIdx]));
      setFeedbackOpen(null);
      setFeedbackData({ correctPlate: '', correctVehicleType: '', notes: '' });
    } catch (err) {
      setError('Failed to submit feedback: ' + err.message);
    }
  }, [file, result, feedbackData]);

  const handleFullImageFeedback = useCallback(async () => {
    try {
      await api.submitFullImageFeedback({
        file,
        accuracyRating: fullFeedbackData.accuracyRating,
        missedVehicles: fullFeedbackData.missedVehicles,
        falseDetections: fullFeedbackData.falseDetections,
        notes: fullFeedbackData.notes,
        totalDetected: result?.detections || 0,
      });
      setFullFeedbackSent(true);
      setFullFeedbackOpen(false);
    } catch (err) {
      setError('Failed to submit full-image feedback: ' + err.message);
    }
  }, [file, result, fullFeedbackData]);

  return (
    <div className="page">
      <div className="page-header">
        <h2>Image Verification</h2>
        <p>Upload a photo to run the full SVIES pipeline — see every detection step</p>
      </div>

      {/* Upload Area */}
      <div
        className="card"
        onDrop={handleDrop}
        onDragOver={e => e.preventDefault()}
        style={{
          border: '2px dashed var(--border-default)',
          textAlign: 'center',
          padding: preview ? 20 : 50,
          cursor: 'pointer',
          marginBottom: 20,
        }}
        onClick={() => !preview && fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={e => handleFile(e.target.files[0])}
        />
        {preview ? (
          <div>
            <img src={preview} alt="Upload preview" style={{
              maxHeight: 300, maxWidth: '100%', borderRadius: 8,
              border: '1px solid var(--border-default)', marginBottom: 16,
            }} />
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button
                className="btn btn-primary"
                onClick={(e) => { e.stopPropagation(); handleUpload(); }}
                disabled={loading}
                style={{ fontSize: 16, padding: '12px 32px' }}
              >
                {loading ? '⏳ Analyzing...' : '🔍 Run Full Pipeline'}
              </button>
              <button
                className="btn btn-outline"
                onClick={(e) => { e.stopPropagation(); setFile(null); setPreview(null); setResult(null); }}
              >
                ✕ Clear
              </button>
            </div>
          </div>
        ) : (
          <>
            <ImagePlus size={48} color="var(--text-muted)" style={{ marginBottom: 16, margin: '0 auto' }} />
            <h3 style={{ marginBottom: 8, color: 'var(--text-primary)' }}>
              Drop an image here or click to browse
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              JPG, PNG — Indian vehicle images for best results
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="card" style={{ borderColor: '#ef4444', color: '#fca5a5', marginBottom: 20 }}>
          ⚠️ {error}
        </div>
      )}

      {loading && (
        <div className="card" style={{ marginBottom: 20, textAlign: 'center', padding: 40 }}>
          <div className="spinner" style={{ margin: '0 auto 16px' }}></div>
          <h3 style={{ color: 'var(--text-secondary)' }}>Running 7-layer pipeline...</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Detection → OCR → Fake Plate → DB Lookup → Safety → Risk Score → Alert
          </p>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Annotated Image + Summary */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
            <div className="card">
              <div className="card-title">📸 Annotated Detection</div>
              {result.annotated_image && (
                <img src={result.annotated_image} alt="Annotated"
                  style={{ width: '100%', borderRadius: 8, border: '1px solid var(--border-default)' }} />
              )}
            </div>
            <div className="card">
              <div className="card-title">{result.detection_summary?.icon} Detection Summary</div>
              <div className="kpi-grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: 16 }}>
                <div className="kpi-card accent">
                  <div className="kpi-label">Vehicles Found</div>
                  <div className="kpi-value" style={{ fontSize: 32 }}>{result.detections}</div>
                </div>
                <div className="kpi-card success">
                  <div className="kpi-label">Pipelines Run</div>
                  <div className="kpi-value" style={{ fontSize: 32 }}>{result.pipeline_results?.length || 0}</div>
                </div>
              </div>
              {result.detection_summary?.vehicles?.map((v, i) => (
                <div key={i} style={{
                  padding: '10px 14px', marginBottom: 8, borderRadius: 8,
                  background: 'var(--bg-secondary)', border: '1px solid var(--border-default)',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div>
                    <span style={{ fontWeight: 700 }}>🚗 {v.type}</span>
                    <span style={{ color: 'var(--text-muted)', marginLeft: 10 }}>{v.color}</span>
                  </div>
                  <span style={{ fontFamily: 'monospace', color: 'var(--text-accent)' }}>
                    {v.confidence}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Per-Vehicle Pipeline Steps */}
          {(result.pipeline_results || []).map((vp, vi) => (
            <div key={vi} className="card" style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div className="card-title" style={{ margin: 0 }}>
                  🚘 Vehicle #{vi + 1}: {vp.vehicle_type}
                  {vp.plate && (
                    <span style={{
                      marginLeft: 12, fontFamily: 'monospace', fontSize: 16,
                      background: 'var(--bg-secondary)', padding: '4px 12px',
                      borderRadius: 6, letterSpacing: 2, fontWeight: 800,
                      color: 'var(--text-accent)',
                    }}>
                      {vp.plate}
                    </span>
                  )}
                </div>
                {vp.plate_crop && (
                  <img src={vp.plate_crop} alt="Plate crop" style={{
                    height: 40, borderRadius: 4, border: '1px solid var(--border-default)',
                  }} />
                )}
              </div>

              {/* Pipeline Steps Timeline */}
              {(vp.steps || []).map((step, si) => (
                <PipelineStep key={si} step={step} index={si} />
              ))}

              {/* Feedback Button */}
              {vp.plate && (
                <div style={{ marginTop: 12, textAlign: 'right' }}>
                  {feedbackOpen === vi ? (
                    <div style={{ background: 'var(--bg-secondary)', padding: 16, borderRadius: 8, textAlign: 'left' }}>
                      <div style={{ fontWeight: 600, marginBottom: 10 }}>📝 Submit Correction</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                        <input className="input" placeholder="Correct plate number"
                          value={feedbackData.correctPlate}
                          onChange={e => setFeedbackData(d => ({ ...d, correctPlate: e.target.value }))} />
                        <input className="input" placeholder="Correct vehicle type"
                          value={feedbackData.correctVehicleType}
                          onChange={e => setFeedbackData(d => ({ ...d, correctVehicleType: e.target.value }))} />
                      </div>
                      <textarea className="input" placeholder="Additional notes..."
                        style={{ marginTop: 10, minHeight: 60 }}
                        value={feedbackData.notes}
                        onChange={e => setFeedbackData(d => ({ ...d, notes: e.target.value }))} />
                      <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
                        <button className="btn btn-primary" onClick={() => handleFeedback(vi)}>
                          ✅ Submit Feedback
                        </button>
                        <button className="btn btn-outline" onClick={() => setFeedbackOpen(null)}>
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button className="btn btn-outline" onClick={() => {
                      setFeedbackOpen(vi);
                      setFeedbackData({ correctPlate: '', correctVehicleType: '', notes: '' });
                    }}
                      style={{ fontSize: 12 }}>
                      {feedbackSentFor.has(vi) ? '✅ Feedback Sent' : '📝 Correct This Detection'}
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}

          {/* Full Image Feedback Card */}
          {result.detections > 0 && (
            <div className="card" style={{ marginBottom: 20, border: '1px solid var(--border-default)' }}>
              <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                📋 Full Image Feedback
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 12 }}>
                Rate the overall accuracy of this scan — help us improve detection quality.
              </p>

              {fullFeedbackSent ? (
                <div style={{
                  padding: '16px 20px', borderRadius: 8,
                  background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)',
                  textAlign: 'center',
                }}>
                  <span style={{ fontSize: 20, marginRight: 8 }}>✅</span>
                  <span style={{ color: '#4ade80', fontWeight: 600 }}>Thank you! Full-image feedback submitted successfully.</span>
                </div>
              ) : fullFeedbackOpen ? (
                <div style={{ background: 'var(--bg-secondary)', padding: 16, borderRadius: 8 }}>
                  {/* Star Rating */}
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Overall Accuracy</div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {[1, 2, 3, 4, 5].map(star => (
                        <button
                          key={star}
                          onClick={() => setFullFeedbackData(d => ({ ...d, accuracyRating: star }))}
                          style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            fontSize: 28, padding: 2, transition: 'transform 0.15s',
                            transform: fullFeedbackData.accuracyRating >= star ? 'scale(1.15)' : 'scale(1)',
                            filter: fullFeedbackData.accuracyRating >= star ? 'none' : 'grayscale(1) opacity(0.4)',
                          }}
                          title={`${star} star${star > 1 ? 's' : ''}`}
                        >
                          ⭐
                        </button>
                      ))}
                      <span style={{ marginLeft: 8, color: 'var(--text-muted)', fontSize: 13, alignSelf: 'center' }}>
                        {fullFeedbackData.accuracyRating > 0 ? `${fullFeedbackData.accuracyRating}/5` : 'Select rating'}
                      </span>
                    </div>
                  </div>

                  {/* Missed & False Detections */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
                    <div>
                      <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Missed Vehicles</label>
                      <input className="input" type="number" min="0" max="20" placeholder="0"
                        value={fullFeedbackData.missedVehicles || ''}
                        onChange={e => setFullFeedbackData(d => ({ ...d, missedVehicles: parseInt(e.target.value) || 0 }))} />
                    </div>
                    <div>
                      <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>False Detections</label>
                      <input className="input" type="number" min="0" max="20" placeholder="0"
                        value={fullFeedbackData.falseDetections || ''}
                        onChange={e => setFullFeedbackData(d => ({ ...d, falseDetections: parseInt(e.target.value) || 0 }))} />
                    </div>
                  </div>

                  {/* Notes */}
                  <textarea className="input" placeholder="Any other feedback about the scan output..."
                    style={{ minHeight: 60, marginBottom: 12 }}
                    value={fullFeedbackData.notes}
                    onChange={e => setFullFeedbackData(d => ({ ...d, notes: e.target.value }))} />

                  <div style={{ display: 'flex', gap: 10 }}>
                    <button className="btn btn-primary" onClick={handleFullImageFeedback}
                      disabled={fullFeedbackData.accuracyRating === 0}>
                      ✅ Submit Full-Image Feedback
                    </button>
                    <button className="btn btn-outline" onClick={() => setFullFeedbackOpen(false)}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button className="btn btn-outline" onClick={() => {
                  setFullFeedbackOpen(true);
                  setFullFeedbackData({ accuracyRating: 0, missedVehicles: 0, falseDetections: 0, notes: '' });
                }}
                  style={{ fontSize: 13, width: '100%', padding: '10px 16px' }}>
                  📋 Rate Full Scan Accuracy & Submit Feedback
                </button>
              )}
            </div>
          )}

          {/* No detections */}
          {result.detections === 0 && (
            <div className="card">
              <div className="empty-state">
                <div className="empty-state-icon">🔍</div>
                <div className="empty-state-title">No vehicles detected</div>
                <div className="empty-state-text">Try a different image with clearer vehicle visibility</div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
