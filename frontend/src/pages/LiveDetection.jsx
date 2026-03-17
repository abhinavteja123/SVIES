import { useState, useEffect, useRef, useCallback } from 'react';
import { api, connectLiveFeed } from '../api';
import { StatusBadge } from '../components';

const VERIFY_BADGE = {
  groq_verified: { label: 'Groq Verified', bg: 'rgba(34,197,94,0.18)', color: '#4ade80', icon: '\u2705' },
  groq_corrected: { label: 'Groq Corrected', bg: 'rgba(59,130,246,0.18)', color: '#60a5fa', icon: '\uD83E\uDD16' },
  easyocr: { label: 'EasyOCR Only', bg: 'rgba(245,158,11,0.15)', color: '#fbbf24', icon: '\uD83D\uDD24' },
  none: { label: 'No OCR', bg: 'rgba(100,116,139,0.15)', color: '#94a3b8', icon: '\u2014' },
};

const LEVEL_COLORS = {
  LOW: '#22c55e', MEDIUM: '#f59e0b', HIGH: '#f97316', CRITICAL: '#dc2626',
};

const STEP_STYLES = {
  completed: { bg: 'rgba(34,197,94,0.1)', border: 'rgba(34,197,94,0.3)', dot: '#22c55e' },
  danger: { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', dot: '#ef4444' },
  warning: { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)', dot: '#f59e0b' },
  skipped: { bg: 'rgba(100,116,139,0.1)', border: 'rgba(100,116,139,0.3)', dot: '#64748b' },
  low: { bg: 'rgba(34,197,94,0.1)', border: 'rgba(34,197,94,0.3)', dot: '#22c55e' },
  medium: { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)', dot: '#f59e0b' },
};

export default function LiveDetection() {
  const [mode, setMode] = useState(null); // null | 'video' | 'photo' | 'webcam'
  const [videoFile, setVideoFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState(null);
  const [liveFrame, setLiveFrame] = useState(null);
  const [detections, setDetections] = useState([]);
  const [allDetections, setAllDetections] = useState([]);
  const [error, setError] = useState('');
  const [webcamActive, setWebcamActive] = useState(false);
  const [webcamLoading, setWebcamLoading] = useState(false);

  // Photo mode state
  const [photoFile, setPhotoFile] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [photoResult, setPhotoResult] = useState(null);
  const [photoLoading, setPhotoLoading] = useState(false);

  const fileRef = useRef(null);
  const photoRef = useRef(null);
  const pollRef = useRef(null);

  // Track which plates we've already added to history (dedup by plate+alert)
  const seenPlatesRef = useRef(new Map()); // plate -> last added timestamp

  // Connect to live feed WebSocket when webcam is active or video is processing
  useEffect(() => {
    if (!webcamActive && !processing) return;

    // Reset seen plates when starting a new session
    seenPlatesRef.current = new Map();

    const DEDUP_COOLDOWN_MS = 60_000; // 60s — match backend cooldown

    const cleanup = connectLiveFeed((data) => {
      if (data.frame) setLiveFrame(data.frame);
      if (data.detections) {
        setDetections(data.detections);

        // Only add genuinely new detections to history (deduplicate by plate)
        const now = Date.now();
        const newEntries = data.detections.filter((d) => {
          if (!d.plate || d.plate === 'UNKNOWN') return false;
          const key = d.plate;
          const lastSeen = seenPlatesRef.current.get(key) || 0;
          if (now - lastSeen < DEDUP_COOLDOWN_MS) return false;
          seenPlatesRef.current.set(key, now);
          return true;
        });

        if (newEntries.length > 0) {
          setAllDetections((prev) => [...newEntries, ...prev].slice(0, 100));
        }
      }
    });
    return cleanup;
  }, [webcamActive, processing]);

  // Poll processing status
  useEffect(() => {
    if (!processing) return;
    pollRef.current = setInterval(async () => {
      try {
        const s = await api.getProcessStatus();
        setStatus(s);
        if (!s.active && !s.error) {
          setProcessing(false);
          clearInterval(pollRef.current);
        }
        if (s.error) {
          setError(s.error);
          setProcessing(false);
          clearInterval(pollRef.current);
        }
      } catch { /* ignore */ }
    }, 1000);
    return () => clearInterval(pollRef.current);
  }, [processing]);

  const handleVideoUpload = useCallback(async () => {
    if (!videoFile) return;
    setUploading(true);
    setError('');
    setAllDetections([]);
    try {
      await api.processVideo(videoFile);
      setProcessing(true);
      setUploading(false);
    } catch (err) {
      setError(err.message);
      setUploading(false);
    }
  }, [videoFile]);

  const handlePhotoFile = useCallback((f) => {
    if (!f || !f.type.startsWith('image/')) return;
    setPhotoFile(f);
    setPhotoResult(null);
    setError('');
    const reader = new FileReader();
    reader.onload = (e) => setPhotoPreview(e.target.result);
    reader.readAsDataURL(f);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file) return;
    if (file.type.startsWith('video/')) {
      setMode('video');
      setVideoFile(file);
    } else if (file.type.startsWith('image/')) {
      setMode('photo');
      handlePhotoFile(file);
    }
  }, [handlePhotoFile]);

  const handlePhotoUpload = useCallback(async () => {
    if (!photoFile) return;
    setPhotoLoading(true);
    setError('');
    setPhotoResult(null);
    try {
      const res = await api.processImage(photoFile);
      setPhotoResult(res);
    } catch (err) {
      setError(err.message || 'Failed to process image');
    } finally {
      setPhotoLoading(false);
    }
  }, [photoFile]);

  const handleWebcamStart = useCallback(async () => {
    setWebcamLoading(true);
    setError('');
    setAllDetections([]);
    setDetections([]);
    try {
      await api.startWebcam();
      setWebcamActive(true);
      setMode('webcam');
    } catch (err) {
      setError(err.message || 'Failed to start webcam');
    } finally {
      setWebcamLoading(false);
    }
  }, []);

  const handleWebcamStop = useCallback(async () => {
    try {
      await api.stopWebcam();
    } catch { /* ignore */ }
    setWebcamActive(false);
    setLiveFrame(null);
  }, []);

  const resetAll = () => {
    if (webcamActive) handleWebcamStop();
    setMode(null);
    setVideoFile(null);
    setLiveFrame(null);
    setStatus(null);
    setAllDetections([]);
    setDetections([]);
    setPhotoFile(null);
    setPhotoPreview(null);
    setPhotoResult(null);
    setWebcamActive(false);
    setError('');
  };

  const progressPct = status?.progress_percent || 0;

  return (
    <div className="page">
      <div className="page-header">
        <h2>Live Detection</h2>
        <p>Upload a video or photo to run the SVIES detection pipeline</p>
      </div>

      {/* ── Mode Selector (shown when nothing is active) ── */}
      {!mode && !processing && !liveFrame && (
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20, marginBottom: 20 }}
        >
          {/* Video Upload Card */}
          <div
            className="card"
            style={{
              border: '2px dashed var(--border-default)',
              textAlign: 'center',
              padding: 40,
              cursor: 'pointer',
              transition: 'border-color 0.2s, transform 0.2s',
            }}
            onClick={() => { setMode('video'); setTimeout(() => fileRef.current?.click(), 50); }}
          >
            <div style={{ fontSize: 48, marginBottom: 14 }}>🎬</div>
            <h3 style={{ marginBottom: 8, color: 'var(--text-primary)' }}>Upload Video</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 0 }}>
              MP4, AVI, MOV — Process frames through full pipeline
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 6 }}>
              Real-time annotated feed with violation detection
            </p>
          </div>

          {/* Photo Upload Card */}
          <div
            className="card"
            style={{
              border: '2px dashed var(--border-default)',
              textAlign: 'center',
              padding: 40,
              cursor: 'pointer',
              transition: 'border-color 0.2s, transform 0.2s',
            }}
            onClick={() => { setMode('photo'); setTimeout(() => photoRef.current?.click(), 50); }}
          >
            <div style={{ fontSize: 48, marginBottom: 14 }}>📷</div>
            <h3 style={{ marginBottom: 8, color: 'var(--text-primary)' }}>Upload Photo</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 0 }}>
              JPG, PNG — Run 7-layer pipeline on a single image
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 6 }}>
              See every detection step: OCR, fake plate, DB lookup, safety
            </p>
          </div>

          {/* Live Camera Card */}
          <div
            className="card"
            style={{
              border: '2px dashed var(--accent-blue, #3b82f6)',
              textAlign: 'center',
              padding: 40,
              cursor: webcamLoading ? 'wait' : 'pointer',
              transition: 'border-color 0.2s, transform 0.2s',
              background: 'rgba(59,130,246,0.04)',
            }}
            onClick={handleWebcamStart}
          >
            <div style={{ fontSize: 48, marginBottom: 14 }}>🎥</div>
            <h3 style={{ marginBottom: 8, color: 'var(--text-primary)' }}>
              {webcamLoading ? 'Starting Camera...' : 'Live Camera'}
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 0 }}>
              Open laptop webcam for real-time detection
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 6 }}>
              Live vehicle, plate & violation detection with Groq AI
            </p>
          </div>
        </div>
      )}

      {/* Hidden file inputs */}
      <input ref={fileRef} type="file" accept="video/*" style={{ display: 'none' }}
        onChange={e => { if (e.target.files[0]) { setVideoFile(e.target.files[0]); setMode('video'); } }} />
      <input ref={photoRef} type="file" accept="image/*" style={{ display: 'none' }}
        onChange={e => { if (e.target.files[0]) { handlePhotoFile(e.target.files[0]); setMode('photo'); } }} />

      {/* ── Video mode: file selected but not yet uploaded ── */}
      {mode === 'video' && videoFile && !processing && !liveFrame && (
        <div className="card" style={{ textAlign: 'center', padding: 40, marginBottom: 20 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🎬</div>
          <h3 style={{ marginBottom: 8, color: 'var(--text-primary)' }}>{videoFile.name}</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
            {(videoFile.size / 1024 / 1024).toFixed(1)} MB
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button className="btn btn-primary" onClick={handleVideoUpload} disabled={uploading}
              style={{ fontSize: 16, padding: '12px 32px' }}>
              {uploading ? 'Uploading...' : 'Start Detection Pipeline'}
            </button>
            <button className="btn btn-secondary" onClick={resetAll}>Cancel</button>
          </div>
        </div>
      )}

      {/* ── Photo mode: file selected, preview shown ── */}
      {mode === 'photo' && photoPreview && !photoResult && !photoLoading && (
        <div className="card" style={{ textAlign: 'center', padding: 30, marginBottom: 20 }}>
          <img src={photoPreview} alt="Preview" style={{
            maxHeight: 320, maxWidth: '100%', borderRadius: 8,
            border: '1px solid var(--border-default)', marginBottom: 16,
          }} />
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button className="btn btn-primary" onClick={handlePhotoUpload}
              style={{ fontSize: 16, padding: '12px 32px' }}>
              Run Full Pipeline
            </button>
            <button className="btn btn-secondary" onClick={resetAll}>Cancel</button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card" style={{ borderColor: '#ef4444', padding: '14px 20px', marginBottom: 20 }}>
          <span style={{ color: '#fca5a5' }}>Error: {error}</span>
        </div>
      )}

      {/* ═══════════ Photo Pipeline Results ═══════════ */}
      {photoLoading && (
        <div className="card" style={{ marginBottom: 20, textAlign: 'center', padding: 40 }}>
          <div className="spinner" style={{ margin: '0 auto 16px' }}></div>
          <h3 style={{ color: 'var(--text-secondary)' }}>Running 7-layer pipeline...</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Detection → OCR → Fake Plate → DB Lookup → Safety → Risk Score → Alert
          </p>
        </div>
      )}

      {photoResult && (
        <>
          {/* Annotated Image + Summary */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
            <div className="card">
              <div className="card-title">Annotated Detection</div>
              {photoResult.annotated_image && (
                <img src={photoResult.annotated_image} alt="Annotated"
                  style={{ width: '100%', borderRadius: 8, border: '1px solid var(--border-default)' }} />
              )}
            </div>
            <div className="card">
              <div className="card-title">Detection Summary</div>
              <div className="kpi-grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: 16 }}>
                <div className="kpi-card accent">
                  <div className="kpi-label">Vehicles Found</div>
                  <div className="kpi-value" style={{ fontSize: 32 }}>{photoResult.detections}</div>
                </div>
                <div className="kpi-card success">
                  <div className="kpi-label">Pipelines Run</div>
                  <div className="kpi-value" style={{ fontSize: 32 }}>{photoResult.pipeline_results?.length || 0}</div>
                </div>
              </div>
              {photoResult.detection_summary?.vehicles?.map((v, i) => (
                <div key={i} style={{
                  padding: '10px 14px', marginBottom: 8, borderRadius: 8,
                  background: 'var(--bg-secondary)', border: '1px solid var(--border-default)',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div>
                    <span style={{ fontWeight: 700 }}>{v.type}</span>
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
          {(photoResult.pipeline_results || []).map((vp, vi) => (
            <div key={vi} className="card" style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div className="card-title" style={{ margin: 0 }}>
                  Vehicle #{vi + 1}: {vp.vehicle_type}
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
              {(vp.steps || []).map((step, si) => {
                const sty = STEP_STYLES[step.status] || STEP_STYLES.completed;
                const isOCRStep = step.name && step.name.includes('OCR');
                const vb = step.verified_by;
                const badge = vb && VERIFY_BADGE[vb];
                return (
                  <div key={si} style={{
                    display: 'flex', alignItems: 'flex-start', gap: 14,
                    padding: '14px 16px', marginBottom: 2, borderRadius: 8,
                    background: sty.bg, borderLeft: `3px solid ${sty.border}`,
                  }}>
                    <div style={{
                      width: 32, height: 32, borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 16, flexShrink: 0, background: 'var(--bg-secondary)',
                      border: `2px solid ${sty.dot}`,
                    }}>
                      {step.icon}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
                        {step.name}
                        {isOCRStep && badge && (
                          <span style={{
                            display: 'inline-flex', alignItems: 'center', gap: 4,
                            padding: '2px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700,
                            background: badge.bg, color: badge.color,
                            border: `1px solid ${badge.color}33`,
                          }}>
                            {badge.icon} {badge.label}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{step.detail}</div>
                      {/* Groq correction comparison */}
                      {isOCRStep && step.raw_text && vb === 'groq_corrected' && (
                        <div style={{
                          marginTop: 6, padding: '6px 10px', borderRadius: 6,
                          background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)',
                          fontSize: 12, fontFamily: 'monospace',
                        }}>
                          <span style={{ color: '#94a3b8' }}>EasyOCR: </span>
                          <span style={{ color: '#f87171', textDecoration: 'line-through' }}>{step.raw_text}</span>
                          <span style={{ color: '#94a3b8', margin: '0 6px' }}>&rarr;</span>
                          <span style={{ color: '#4ade80', fontWeight: 700 }}>Groq AI: {step.detail?.match(/Plate: (\S+)/)?.[1] || '\u2014'}</span>
                        </div>
                      )}
                      {isOCRStep && vb === 'groq_verified' && (
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
                            }}>{f}</span>
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
                            }}>{v}</span>
                          ))}
                        </div>
                      )}
                      {step.breakdown && (
                        <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text-muted)' }}>
                          {Object.entries(step.breakdown).map(([k, val]) => (
                            <span key={k} style={{ marginRight: 12 }}>{k}: +{val}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}

          {photoResult.detections === 0 && (
            <div className="card" style={{ textAlign: 'center', padding: 40 }}>
              <h3 style={{ color: 'var(--text-secondary)' }}>No vehicles detected</h3>
              <p style={{ color: 'var(--text-muted)' }}>Try a different image with clearer vehicle visibility</p>
            </div>
          )}

          <div style={{ textAlign: 'center', marginTop: 10, marginBottom: 20 }}>
            <button className="btn btn-primary" onClick={resetAll}>
              Process Another File
            </button>
          </div>
        </>
      )}

      {/* ═══════════ Video Processing Progress ═══════════ */}
      {processing && status && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title">Processing Video</div>
          <div style={{ marginBottom: 12 }}>
            <div style={{
              height: 8, borderRadius: 4,
              background: 'var(--bg-secondary)',
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                width: `${progressPct}%`,
                background: 'var(--accent-gradient)',
                borderRadius: 4,
                transition: 'width 0.3s ease',
              }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 12, color: 'var(--text-muted)' }}>
              <span>{progressPct}% complete</span>
              <span>Frame {status.processed_frames}/{status.total_frames}</span>
            </div>
          </div>
          <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
            <div className="kpi-card accent">
              <div className="kpi-label">Detections</div>
              <div className="kpi-value" style={{ fontSize: 28 }}>{status.detections}</div>
            </div>
            <div className="kpi-card danger">
              <div className="kpi-label">Violations</div>
              <div className="kpi-value" style={{ fontSize: 28 }}>{status.violations}</div>
            </div>
            <div className="kpi-card success">
              <div className="kpi-label">Frames</div>
              <div className="kpi-value" style={{ fontSize: 28 }}>{status.processed_frames}</div>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════ Live Video Feed + Detection Panel ═══════════ */}
      {(liveFrame || processing || webcamActive) && (
        <>
          {/* Webcam control bar */}
          {webcamActive && (
            <div className="card" style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 20px', marginBottom: 16,
              background: 'rgba(59,130,246,0.08)', borderColor: 'rgba(59,130,246,0.3)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: '#ef4444', display: 'inline-block',
                  animation: 'pulse 1.5s infinite',
                }} />
                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                  LIVE - Webcam Active
                </span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  Groq AI + EasyOCR verification enabled
                </span>
              </div>
              <button
                className="btn btn-secondary"
                onClick={handleWebcamStop}
                style={{ background: 'rgba(239,68,68,0.15)', borderColor: '#ef4444', color: '#fca5a5' }}
              >
                Stop Camera
              </button>
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20, marginBottom: 20 }}>
          <div className="card">
            <div className="card-title">Live Annotated Feed</div>
            {liveFrame ? (
              <img
                src={`data:image/jpeg;base64,${liveFrame}`}
                alt="Live Detection"
                style={{ width: '100%', borderRadius: 8, border: '1px solid var(--border-default)' }}
              />
            ) : (
              <div className="empty-state" style={{ padding: 60 }}>
                <h3>Waiting for frames...</h3>
                <p>Processing will begin shortly</p>
              </div>
            )}
          </div>

          <div className="card" style={{ maxHeight: 500, overflowY: 'auto' }}>
            <div className="card-title">Live Detections</div>
            {detections.length === 0 && !processing ? (
              <div className="empty-state" style={{ padding: 30 }}>
                <h3>No detections yet</h3>
              </div>
            ) : (
              detections.map((d, i) => (
                <div key={i} style={{
                  padding: '10px 12px', marginBottom: 8, borderRadius: 8,
                  background: 'var(--bg-secondary)',
                  border: `1px solid ${d.alert_level === 'CRITICAL' || d.alert_level === 'HIGH' ? 'rgba(239,68,68,0.3)' : 'var(--border-default)'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 14, letterSpacing: 1 }}>
                      {d.plate}
                    </span>
                    <StatusBadge level={d.alert_level} />
                  </div>
                  {d.timestamp && (
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>
                      {new Date(d.timestamp).toLocaleString()}
                    </div>
                  )}
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {d.vehicle_type} | Risk: {d.risk_score}
                    {d.fake_plate && ' | FAKE PLATE'}
                    {d.stolen && ' | STOLEN'}
                  </div>
                  {d.verified_by && VERIFY_BADGE[d.verified_by] && d.verified_by !== 'none' && (
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 3,
                      padding: '1px 8px', borderRadius: 10, fontSize: 10, fontWeight: 700, marginTop: 4,
                      background: VERIFY_BADGE[d.verified_by].bg,
                      color: VERIFY_BADGE[d.verified_by].color,
                    }}>
                      {VERIFY_BADGE[d.verified_by].icon} {VERIFY_BADGE[d.verified_by].label}
                    </span>
                  )}
                  {d.violations && d.violations.length > 0 && (
                    <div style={{ fontSize: 11, color: '#fca5a5', marginTop: 4 }}>
                      {d.violations.join(', ')}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
        </>
      )}

      {/* ═══════════ Detection History Table ═══════════ */}
      {allDetections.length > 0 && (
        <div className="card">
          <div className="card-title">Detection History ({allDetections.length} records)</div>
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Plate</th><th>Vehicle</th><th>Timestamp</th><th>Risk</th><th>Level</th>
                  <th>Owner</th><th>Violations</th>
                </tr>
              </thead>
              <tbody>
                {allDetections.slice(0, 30).map((d, i) => (
                  <tr key={i}>
                    <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{d.plate}</td>
                    <td>{d.vehicle_type}</td>
                    <td style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                      {d.timestamp ? new Date(d.timestamp).toLocaleString() : '\u2014'}
                    </td>
                    <td style={{ fontWeight: 700, color: LEVEL_COLORS[d.alert_level] || '#64748b' }}>
                      {d.risk_score}
                    </td>
                    <td><StatusBadge level={d.alert_level} /></td>
                    <td style={{ fontSize: 12 }}>{d.owner || 'Unknown'}</td>
                    <td style={{ fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {(d.violations || []).join(', ') || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Re-upload button (after video finishes) */}
      {!processing && !webcamActive && liveFrame && (
        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <button className="btn btn-primary" onClick={resetAll}>
            Process Another File
          </button>
        </div>
      )}
    </div>
  );
}
