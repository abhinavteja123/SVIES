import { useAuth } from '../context/AuthContext';

export default function Header({ title, subtitle, children }) {
  const { role } = useAuth();

  return (
    <div className="page-header">
      <div className="flex-between">
        <div>
          <h2>
            {title}
            {role && <span className="badge badge-role">{role}</span>}
          </h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {children && <div className="flex-gap">{children}</div>}
      </div>
    </div>
  );
}
