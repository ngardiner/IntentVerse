import React from 'react';

/**
 * Component to display compatibility status for content packs
 */
const CompatibilityStatus = ({ 
  compatibility, 
  showDetails = false, 
  className = '' 
}) => {
  if (!compatibility) {
    return null;
  }

  const { compatible, reasons, conditions, has_conditions, app_version } = compatibility;

  const getStatusIcon = () => {
    if (!has_conditions) {
      return <span className="status-icon universal" title="Universal compatibility">🌐</span>;
    }
    return compatible 
      ? <span className="status-icon compatible" title="Compatible">✅</span>
      : <span className="status-icon incompatible" title="Incompatible">❌</span>;
  };

  const getStatusText = () => {
    if (!has_conditions) {
      return 'Universal compatibility';
    }
    return compatible ? 'Compatible' : 'Incompatible';
  };

  const getStatusClass = () => {
    if (!has_conditions) return 'compatibility-universal';
    return compatible ? 'compatibility-compatible' : 'compatibility-incompatible';
  };

  return (
    <div className={`compatibility-status ${getStatusClass()} ${className}`}>
      <div className="compatibility-summary">
        {getStatusIcon()}
        <span className="status-text">{getStatusText()}</span>
        {app_version && (
          <span className="app-version" title={`IntentVerse version: ${app_version}`}>
            (v{app_version})
          </span>
        )}
      </div>

      {showDetails && (
        <div className="compatibility-details">
          {!compatible && reasons && reasons.length > 0 && (
            <div className="incompatibility-reasons">
              <strong>Issues:</strong>
              <ul>
                {reasons.map((reason, index) => (
                  <li key={index} className="reason-item">{reason}</li>
                ))}
              </ul>
            </div>
          )}

          {conditions && conditions.length > 0 && (
            <div className="compatibility-conditions">
              <strong>Requirements:</strong>
              <ul>
                {conditions.map((condition, index) => (
                  <li key={index} className="condition-item">
                    {condition.type === 'version_range' && (
                      <span>
                        Version: {condition.min_version || 'any'}
                        {condition.max_version && ` - ${condition.max_version}`}
                        {condition.reason && (
                          <span className="condition-reason"> ({condition.reason})</span>
                        )}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .compatibility-status {
          display: flex;
          flex-direction: column;
          gap: 8px;
          padding: 8px;
          border-radius: 4px;
          font-size: 14px;
        }

        .compatibility-compatible {
          background-color: #f0f9ff;
          border: 1px solid #bae6fd;
          color: #0c4a6e;
        }

        .compatibility-incompatible {
          background-color: #fef2f2;
          border: 1px solid #fecaca;
          color: #991b1b;
        }

        .compatibility-universal {
          background-color: #f9fafb;
          border: 1px solid #d1d5db;
          color: #374151;
        }

        .compatibility-summary {
          display: flex;
          align-items: center;
          gap: 6px;
          font-weight: 500;
        }

        .status-icon {
          font-size: 16px;
        }

        .app-version {
          font-size: 12px;
          opacity: 0.7;
          margin-left: auto;
        }

        .compatibility-details {
          margin-top: 8px;
          padding-top: 8px;
          border-top: 1px solid rgba(0, 0, 0, 0.1);
        }

        .incompatibility-reasons,
        .compatibility-conditions {
          margin-bottom: 8px;
        }

        .incompatibility-reasons strong,
        .compatibility-conditions strong {
          display: block;
          margin-bottom: 4px;
          font-size: 13px;
        }

        .incompatibility-reasons ul,
        .compatibility-conditions ul {
          margin: 0;
          padding-left: 16px;
          list-style-type: disc;
        }

        .reason-item,
        .condition-item {
          margin-bottom: 2px;
          font-size: 13px;
          line-height: 1.4;
        }

        .condition-reason {
          font-style: italic;
          opacity: 0.8;
        }

        /* Compact mode */
        .compatibility-status.compact {
          padding: 4px 8px;
          flex-direction: row;
          align-items: center;
        }

        .compatibility-status.compact .compatibility-details {
          margin-top: 0;
          margin-left: 12px;
          padding-top: 0;
          border-top: none;
        }

        /* Inline mode */
        .compatibility-status.inline {
          display: inline-flex;
          padding: 2px 6px;
          border-radius: 12px;
          font-size: 12px;
        }

        .compatibility-status.inline .status-text {
          margin-right: 4px;
        }

        .compatibility-status.inline .app-version {
          display: none;
        }
      `}</style>
    </div>
  );
};

export default CompatibilityStatus;