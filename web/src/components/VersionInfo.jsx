import React, { useState, useEffect } from 'react';
import { getVersionInfo } from '../api/client';
import './VersionInfo.css';

/**
 * Component to display IntentVerse version information
 */
const VersionInfo = ({ 
  showDetails = false, 
  className = '',
  inline = false 
}) => {
  const [versionInfo, setVersionInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchVersionInfo = async () => {
      try {
        setLoading(true);
        const response = await getVersionInfo();
        setVersionInfo(response);
        setError(null);
      } catch (err) {
        console.error('Error fetching version info:', err);
        setError('Failed to load version information');
      } finally {
        setLoading(false);
      }
    };

    fetchVersionInfo();
  }, []);

  if (loading) {
    return (
      <div className={`version-info loading ${className}`}>
        <span>Loading version...</span>
      </div>
    );
  }

  if (error) {
    // Show a fallback version when API fails
    if (inline) {
      return (
        <span className={`version-info inline ${className}`} title={error}>
          IntentVerse v1.1.0
        </span>
      );
    }
    return (
      <div className={`version-info error ${className}`}>
        <span>⚠️ {error}</span>
      </div>
    );
  }

  if (!versionInfo) {
    return null;
  }

  const { version, major, minor, patch, semantic_version } = versionInfo;

  // Fallback to hardcoded version if API response is missing version
  const displayVersion = version || '1.1.0';

  if (inline) {
    return (
      <span className={`version-info inline ${className}`}>
        IntentVerse v{displayVersion}
      </span>
    );
  }

  return (
    <div className={`version-info ${className}`}>
      <div className="version-summary">
        <span className="version-label">IntentVerse</span>
        <span className="version-number">v{displayVersion}</span>
        {semantic_version && (
          <span className="version-badge">SemVer</span>
        )}
      </div>

      {showDetails && (
        <div className="version-details">
          <div className="version-breakdown">
            <span className="breakdown-item">
              <strong>Major:</strong> {major ?? 1}
            </span>
            <span className="breakdown-item">
              <strong>Minor:</strong> {minor ?? 1}
            </span>
            <span className="breakdown-item">
              <strong>Patch:</strong> {patch ?? 0}
            </span>
          </div>
          
          <div className="version-info-text">
            <p>
              This version follows{' '}
              <a 
                href="https://semver.org/" 
                target="_blank" 
                rel="noopener noreferrer"
                className="semver-link"
              >
                Semantic Versioning
              </a>{' '}
              principles for compatibility management.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default VersionInfo;