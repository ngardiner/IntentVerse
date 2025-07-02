import React from 'react';
import './CompatibilityStatus.css';

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
    </div>
  );
};

export default CompatibilityStatus;