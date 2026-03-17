import { NavLink, useNavigate } from 'react-router-dom';
import {
  Shield,
  LayoutDashboard,
  Video,
  ScanSearch,
  Search,
  AlertTriangle,
  BarChart3,
  UserX,
  Map,
  Brain,
  Users,
  Car,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const ROLE_LEVEL = { VIEWER: 0, RTO: 1, POLICE: 2, ADMIN: 3 };

const NAV_LINKS = [
  { to: '/', icon: LayoutDashboard, label: 'Overview' },
  { to: '/detect', icon: Video, label: 'Live Detection' },
  { to: '/verify', icon: ScanSearch, label: 'Image Verify' },
  { to: '/lookup', icon: Search, label: 'Vehicle Lookup' },
  { to: '/violations', icon: AlertTriangle, label: 'Violations' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/offenders', icon: UserX, label: 'Offenders' },
  { to: '/zones', icon: Map, label: 'Zone Map' },
  { to: '/learning', icon: Brain, label: 'Active Learning', minRole: 'ADMIN' },
  { to: '/vehicle-management', icon: Car, label: 'Vehicle Mgmt', minRole: 'RTO' },
  { to: '/users', icon: Users, label: 'User Management', minRole: 'POLICE' },
];

export default function Sidebar() {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();

  const visibleLinks = NAV_LINKS.filter((link) => {
    if (!link.minRole) return true;
    return (ROLE_LEVEL[role] || 0) >= (ROLE_LEVEL[link.minRole] || 0);
  });

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Shield />
        </div>
        <div className="sidebar-title">
          <h1>SVIES</h1>
          <p>Smart Vehicle Intelligence</p>
        </div>
      </div>

      <nav className="sidebar-nav">
        {visibleLinks.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `nav-item${isActive ? ' active' : ''}`
            }
          >
            <span className="icon">
              <Icon />
            </span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="status-dot" />
        <div style={{ flex: 1, overflow: 'hidden' }}>
          {user?.email && (
            <span title={user.email} style={{ display: 'block', fontSize: '0.75rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user.email}
            </span>
          )}
          <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-accent)' }}>
            {role}
          </span>
        </div>
        {user && (
          <button
            onClick={handleLogout}
            className="btn btn-icon"
            style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              color: 'var(--color-danger)',
              padding: 6,
              flexShrink: 0,
            }}
            title="Sign out"
          >
            <LogOut size={16} />
          </button>
        )}
      </div>
    </aside>
  );
}
