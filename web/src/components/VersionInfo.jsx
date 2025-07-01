import React, { useState, useEffect } from 'react';
import { getVersionInfo } from '../api/client';

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

  if (inline) {
    return (
      <span className={`version-info inline ${className}`}>
        IntentVerse v{version}
      </span>
    );
  }

  return (
    <div className={`version-info ${className}`}>
      <div className="version-summary">
        <span className="version-label">IntentVerse</span>
        <span className="version-number">v{version}</span>
        {semantic_version && (
          <span className="version-badge">SemVer</span>
        )}
      </div>

      {showDetails && (
        <div className="version-details">
          <div className="version-breakdown">
            <span className="breakdown-item">
              <strong>Major:</strong> {major}
            </span>
            <span className="breakdown-item">
              <strong>Minor:</strong> {minor}
            </span>
            <span className="breakdown-item">
              <strong>Patch:</strong> {patch}
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

      <style jsx>{`
        .version-info {
          display: flex;
          flex-direction: column;
          gap: 8px;
          padding: 12px;
          background-color: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          font-size: 14px;
        }

        .version-info.loading,
        .version-info.error {
          padding: 8px 12px;
          text-align: center;
          font-style: italic;
          color: #64748b;
        }

        .version-info.error {
          background-color: #fef2f2;
          border-color: #fecaca;
          color: #dc2626;
        }

        .version-info.inline {
          display: inline;
          padding: 0;
          background: none;
          border: none;
          font-size: inherit;
          color: #64748b;
        }

        .version-summary {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .version-label {
          font-weight: 600;
          color: #1e293b;
        }

        .version-number {
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-weight: 700;
          color: #0f172a;
          background-color: #e2e8f0;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 13px;
        }

        .version-badge {
          background-color: #dbeafe;
          color: #1e40af;
          padding: 2px 6px;
          border-radius: 10px;
          font-size: 11px;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .version-details {
          margin-top: 8px;
          padding-top: 8px;
          border-top: 1px solid #e2e8f0;
        }

        .version-breakdown {
          display: flex;
          gap: 16px;
          margin-bottom: 8px;
        }

        .breakdown-item {
          font-size: 13px;
          color: #475569;
        }

        .breakdown-item strong {
          color: #1e293b;
        }

        .version-info-text {
          font-size: 12px;
          color: #64748b;
          line-height: 1.4;
        }

        .version-info-text p {
          margin: 0;
        }

        .semver-link {
          color: #2563eb;
          text-decoration: none;
        }

        .semver-link:hover {
          text-decoration: underline;
        }

        /* Compact variant */
        .version-info.compact {
          padding: 6px 10px;
          flex-direction: row;
          align-items: center;
        }

        .version-info.compact .version-details {
          margin-top: 0;
          margin-left: 12px;
          padding-top: 0;
          border-top: none;
        }

        .version-info.compact .version-breakdown {
          margin-bottom: 0;
        }

        .version-info.compact .version-info-text {
          display: none;
        }
      `}</style>
    </div>
  );
};

export default VersionInfo;