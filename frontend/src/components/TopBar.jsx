import React from 'react';
import { useAuth } from '../context/AuthContext';

export default function TopBar() {
  const { role } = useAuth();

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h1 className="topbar-title">Smart Vehicle Intelligence & Enforcement System</h1>
      </div>
      <div className="topbar-right">
        <span className="topbar-dept">Ministry of Road Transport & Highways</span>
        <span className="badge badge-medium" style={{ marginLeft: '12px', padding: '6px 12px' }}>
          {role}
        </span>
      </div>
    </header>
  );
}
