import { isValidElement } from 'react';

export default function EmptyState({ icon: Icon, title, message, text, action }) {
  const displayText = message || text;
  return (
    <div className="empty-state">
      {Icon && (
        <div className="empty-state-icon">
          {isValidElement(Icon)
            ? Icon
            : typeof Icon === 'function' || (typeof Icon === 'object' && Icon.$$typeof)
              ? <Icon />
              : null}
        </div>
      )}
      {title && <div className="empty-state-title">{title}</div>}
      {displayText && <div className="empty-state-text">{displayText}</div>}
      {action && (
        <button className="btn btn-primary mt-4" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
}
