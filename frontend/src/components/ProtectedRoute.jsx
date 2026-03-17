import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const ROLE_HIERARCHY = ['VIEWER', 'RTO', 'POLICE', 'ADMIN'];

function getRoleLevel(role) {
  const index = ROLE_HIERARCHY.indexOf(role);
  return index === -1 ? 0 : index;
}

export default function ProtectedRoute({ children, requiredRole }) {
  const { user, role, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <span>Authenticating...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && getRoleLevel(role) < getRoleLevel(requiredRole)) {
    return (
      <div className="page">
        <div className="empty-state">
          <div className="empty-state-icon">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <h2 className="empty-state-title">Access Denied</h2>
          <p className="empty-state-text">
            You do not have permission to view this page.
            Required role: <strong>{requiredRole}</strong>. Your role: <strong>{role}</strong>.
          </p>
        </div>
      </div>
    );
  }

  return children;
}
