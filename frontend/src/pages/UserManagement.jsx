import { useState, useEffect } from 'react';
import { Users, Shield, Mail, ChevronDown, RefreshCw, UserPlus, Trash2, Eye, EyeOff } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { KPICard, LoadingSpinner, EmptyState } from '../components';

const ROLE_STYLES = {
  ADMIN:  { background: 'rgba(99,102,241,0.15)',  color: '#818cf8' },
  POLICE: { background: 'rgba(34,197,94,0.15)',    color: '#4ade80' },
  RTO:    { background: 'rgba(245,158,11,0.15)',   color: '#fbbf24' },
  VIEWER: { background: 'rgba(148,163,184,0.15)',  color: '#94a3b8' },
};

const ALL_ROLE_OPTIONS = ['ADMIN', 'POLICE', 'RTO', 'VIEWER'];
const POLICE_ROLE_OPTIONS = ['RTO', 'VIEWER'];

export default function UserManagement() {
  const { user: currentUser, role: currentUserRole } = useAuth();
  const isAdmin = currentUserRole === 'ADMIN';

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [changingRole, setChangingRole] = useState(null);
  const [deletingUid, setDeletingUid] = useState(null);

  // Add User form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('VIEWER');
  const [newDisplayName, setNewDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [creating, setCreating] = useState(false);

  const roleOptions = isAdmin ? ALL_ROLE_OPTIONS : POLICE_ROLE_OPTIONS;

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getUsers();
      setUsers(data.users || data || []);
    } catch (err) {
      setError(err.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleRoleChange = async (uid, role) => {
    setChangingRole(uid);
    try {
      await api.setUserRole(uid, role);
      toast.success(`Role updated to ${role}`);
      setUsers((prev) => prev.map((u) => (u.uid === uid ? { ...u, role } : u)));
    } catch (err) {
      toast.error(err.message || 'Failed to update role');
    } finally {
      setChangingRole(null);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newEmail || !newPassword) {
      toast.error('Email and password are required');
      return;
    }
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }

    setCreating(true);
    try {
      const result = await api.createUser(newEmail, newPassword, newRole, newDisplayName);
      toast.success(`User ${newEmail} created with role ${newRole}`);
      setUsers((prev) => [...prev, { uid: result.uid, email: newEmail, role: newRole, display_name: newDisplayName }]);
      setNewEmail('');
      setNewPassword('');
      setNewRole('VIEWER');
      setNewDisplayName('');
      setShowAddForm(false);
    } catch (err) {
      toast.error(err.message || 'Failed to create user');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteUser = async (uid, email) => {
    if (uid === currentUser?.uid) {
      toast.error('You cannot delete your own account');
      return;
    }
    if (!window.confirm(`Are you sure you want to delete user "${email || uid}"? This action cannot be undone.`)) {
      return;
    }

    setDeletingUid(uid);
    try {
      await api.deleteUser(uid);
      toast.success(`User ${email || uid} deleted`);
      setUsers((prev) => prev.filter((u) => u.uid !== uid));
    } catch (err) {
      toast.error(err.message || 'Failed to delete user');
    } finally {
      setDeletingUid(null);
    }
  };

  const totalUsers = users.length;
  const adminCount = users.filter((u) => u.role === 'ADMIN').length;
  const policeCount = users.filter((u) => u.role === 'POLICE').length;
  const rtoCount = users.filter((u) => u.role === 'RTO').length;

  const kpis = [
    { label: 'Total Users', value: totalUsers, icon: Users, color: '#6366f1' },
    { label: 'Admins', value: adminCount, icon: Shield, color: '#818cf8' },
    { label: 'Police', value: policeCount, icon: Shield, color: '#4ade80' },
    { label: 'RTO', value: rtoCount, icon: Shield, color: '#fbbf24' },
  ];

  if (currentUserRole !== 'ADMIN' && currentUserRole !== 'POLICE') {
    return (
      <div className="page">
        <EmptyState icon={Shield} title="Access Denied" message="Only administrators and police can manage users." />
      </div>
    );
  }

  if (loading) return <LoadingSpinner message="Loading users..." />;

  if (error) {
    return (
      <div className="page">
        <div className="page-header"><h2>User Management</h2><p>Administration</p></div>
        <div className="card" style={{ padding: '2rem' }}>
          <EmptyState icon={Users} title="Failed to load users" message={error} />
          <div style={{ textAlign: 'center', marginTop: '1rem' }}>
            <button className="btn btn-primary" onClick={fetchUsers}><RefreshCw size={16} /> Retry</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page user-management">
      <div className="page-header">
        <h2>User Management</h2>
        <p>
          {isAdmin
            ? 'Administration \u2014 Create users, assign roles, delete users'
            : 'Add new users to the system'}
        </p>
      </div>

      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <KPICard key={kpi.label} label={kpi.label} value={kpi.value} icon={kpi.icon} color={kpi.color} />
        ))}
      </div>

      {/* Add User Section */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <UserPlus size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />
            Add New User
          </h3>
          <button
            className={`btn ${showAddForm ? 'btn-secondary' : 'btn-primary'}`}
            onClick={() => setShowAddForm(!showAddForm)}
          >
            {showAddForm ? 'Cancel' : 'Add User'}
          </button>
        </div>

        {showAddForm && (
          <div className="card-body" style={{ borderTop: '1px solid rgba(148,163,184,0.08)' }}>
            <form onSubmit={handleCreateUser} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', maxWidth: '700px' }}>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input
                  className="form-input"
                  type="email"
                  placeholder="user@example.com"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Display Name</label>
                <input
                  className="form-input"
                  type="text"
                  placeholder="Officer Name"
                  value={newDisplayName}
                  onChange={(e) => setNewDisplayName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    className="form-input"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min 6 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    minLength={6}
                    style={{ paddingRight: '2.5rem' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)',
                      background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer',
                    }}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Role</label>
                <div style={{ position: 'relative' }}>
                  <select
                    className="form-input"
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    style={{ appearance: 'none', paddingRight: '2rem', cursor: 'pointer' }}
                  >
                    {roleOptions.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                  <ChevronDown
                    size={14}
                    style={{
                      position: 'absolute', right: '0.6rem', top: '50%',
                      transform: 'translateY(-50%)', pointerEvents: 'none', opacity: 0.5,
                    }}
                  />
                </div>
              </div>

              <div style={{ gridColumn: '1 / -1' }}>
                <button className="btn btn-primary" type="submit" disabled={creating} style={{ gap: '8px' }}>
                  <UserPlus size={16} />
                  {creating ? 'Creating...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

      {/* User List Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">All Users ({totalUsers})</h3>
          <button className="btn btn-secondary" onClick={fetchUsers}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
        <div className="card-body">
          {users.length === 0 ? (
            <EmptyState icon={UserPlus} title="No users found" message="Create the first user using the form above." />
          ) : (
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th><Mail size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />Email</th>
                    <th>Name</th>
                    <th>Role</th>
                    <th style={{ fontFamily: 'monospace' }}>UID</th>
                    {isAdmin && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.uid}>
                      <td>{u.email || '--'}</td>
                      <td>{u.display_name || u.displayName || '--'}</td>
                      <td>
                        <span className="badge" style={ROLE_STYLES[u.role] || ROLE_STYLES.VIEWER}>
                          {u.role || 'VIEWER'}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.75rem', opacity: 0.6, maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {u.uid}
                      </td>
                      {isAdmin && (
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {/* Role change dropdown */}
                            <div style={{ position: 'relative', display: 'inline-block' }}>
                              <select
                                className="form-input"
                                value={u.role || 'VIEWER'}
                                disabled={changingRole === u.uid}
                                onChange={(e) => handleRoleChange(u.uid, e.target.value)}
                                style={{ paddingRight: '2rem', minWidth: '110px', cursor: 'pointer', appearance: 'none' }}
                              >
                                {ALL_ROLE_OPTIONS.map((opt) => (
                                  <option key={opt} value={opt}>{opt}</option>
                                ))}
                              </select>
                              <ChevronDown
                                size={14}
                                style={{
                                  position: 'absolute', right: '0.6rem', top: '50%',
                                  transform: 'translateY(-50%)', pointerEvents: 'none', opacity: 0.5,
                                }}
                              />
                            </div>
                            {changingRole === u.uid && (
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                Updating...
                              </span>
                            )}
                            {/* Delete button */}
                            <button
                              className="btn btn-icon"
                              title={u.uid === currentUser?.uid ? 'Cannot delete yourself' : `Delete ${u.email || 'user'}`}
                              disabled={deletingUid === u.uid || u.uid === currentUser?.uid}
                              onClick={() => handleDeleteUser(u.uid, u.email)}
                              style={{
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.2)',
                                color: 'var(--color-danger)',
                                padding: 6,
                                opacity: u.uid === currentUser?.uid ? 0.3 : 1,
                                cursor: u.uid === currentUser?.uid ? 'not-allowed' : 'pointer',
                              }}
                            >
                              <Trash2 size={14} />
                            </button>
                            {deletingUid === u.uid && (
                              <span style={{ fontSize: '0.75rem', color: 'var(--color-danger)' }}>
                                Deleting...
                              </span>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
