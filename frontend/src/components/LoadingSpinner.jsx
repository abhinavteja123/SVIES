export default function LoadingSpinner({ message }) {
  return (
    <div className="skeleton-loader" style={{ padding: '40px', width: '100%', animation: 'skeletonPulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}>
      <div style={{ height: '24px', width: '150px', backgroundColor: 'var(--border-subtle)', borderRadius: '4px', margin: '0 0 24px 0' }}></div>
      <div style={{ height: '44px', width: '100%', backgroundColor: 'var(--bg-card-hover)', borderRadius: '4px', marginBottom: '12px' }}></div>
      <div style={{ height: '44px', width: '100%', backgroundColor: 'var(--bg-card-hover)', borderRadius: '4px', marginBottom: '12px' }}></div>
      <div style={{ height: '44px', width: '100%', backgroundColor: 'var(--bg-card-hover)', borderRadius: '4px', marginBottom: '12px' }}></div>
      {message && <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '24px', fontSize: '13px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{message}</div>}
      <style>{`
        @keyframes skeletonPulse {
          0%, 100% { opacity: 0.7; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}

