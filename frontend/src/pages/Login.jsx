import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Mail, Chrome } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  const { user, loading, login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      navigate('/', { replace: true });
    }
  }, [user, loading, navigate]);

  const handleEmailLogin = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err) {
      const code = err.code || '';
      if (code === 'auth/user-not-found' || code === 'auth/invalid-credential') {
        setError('Access denied. Only authorized personnel can sign in. Contact your administrator.');
      } else if (code === 'auth/wrong-password') {
        setError('Invalid password. Please try again.');
      } else if (code === 'auth/too-many-requests') {
        setError('Too many failed attempts. Account temporarily locked. Try again later.');
      } else {
        setError(err.message || 'Authentication failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setGoogleLoading(true);

    try {
      await loginWithGoogle();
      navigate('/', { replace: true });
    } catch (err) {
      const code = err.code || '';
      if (code === 'auth/popup-closed-by-user') {
        // User closed popup, ignore
      } else if (code === 'auth/unauthorized-domain') {
        setError('This domain is not authorized for Google sign-in. Contact administrator.');
      } else {
        setError('Google sign-in failed. Ensure your account is authorized by an admin.');
      }
    } finally {
      setGoogleLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="loading">
            <div className="spinner"></div>
          </div>
        </div>
      </div>
    );
  }

  if (user) return null;

  return (
    <div className="login-page">
      <div className="login-card" style={{ maxWidth: '440px', width: '100%', padding: '40px', textAlign: 'center', background: 'var(--bg-surface)' }}>
        <p style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '12px', letterSpacing: '0.05em' }}>
          Government of India
        </p>
        <div className="login-logo" style={{ margin: '0 auto 16px', background: 'var(--accent-primary)', color: 'white', width: '48px', height: '48px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Shield size={24} />
        </div>
        <h1 className="login-title" style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '4px' }}>
          SVIES System Login
        </h1>
        <p className="login-subtitle" style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '32px' }}>
          Ministry of Road Transport &amp; Highways
        </p>

        {error && <div className="login-error">{error}</div>}

        <form className="login-form" onSubmit={handleEmailLogin}>
          <div className="form-group">
            <label className="form-label" htmlFor="email">Email Address</label>
            <input
              id="email"
              className="form-input"
              type="email"
              placeholder="Enter your authorized email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password"
              className="form-input"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center', gap: '8px' }}
            disabled={isLoading || googleLoading}
          >
            <Mail size={16} />
            {isLoading ? 'Signing in...' : 'Sign In with Email'}
          </button>
        </form>

        <div style={{
          display: 'flex', alignItems: 'center', gap: '12px',
          margin: '20px 0', color: 'var(--text-muted)', fontSize: '0.75rem',
        }}>
          <div style={{ flex: 1, height: '1px', background: 'rgba(148,163,184,0.15)' }} />
          <span>OR</span>
          <div style={{ flex: 1, height: '1px', background: 'rgba(148,163,184,0.15)' }} />
        </div>

        <button
          type="button"
          className="btn btn-secondary"
          style={{
            width: '100%', justifyContent: 'center', gap: '8px',
            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(148,163,184,0.15)',
          }}
          onClick={handleGoogleLogin}
          disabled={isLoading || googleLoading}
        >
          <Chrome size={16} />
          {googleLoading ? 'Signing in...' : 'Sign In with Google'}
        </button>

        <p style={{
          textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)',
          marginTop: '32px', lineHeight: '1.6', letterSpacing: '0.02em',
        }}>
          Authorized personnel only. Access is logged and monitored.<br/>
          Contact your network administrator for account issues.
        </p>
      </div>
    </div>
  );
}
