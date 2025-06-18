import React, { useState, useEffect } from 'react';
import { previewContentPack } from '../api/client';

const ContentPackPreview = ({ filename, isOpen, onClose, onLoad }) => {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && filename) {
      fetchPreview();
    }
  }, [isOpen, filename]);

  const fetchPreview = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await previewContentPack(filename);
      setPreview(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load preview');
      console.error('Preview error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadPack = () => {
    if (onLoad) {
      onLoad(filename);
    }
    onClose();
  };

  const renderValidationStatus = (validation) => {
    if (!validation) return null;

    return (
      <div className="validation-status">
        <h4>Validation Status</h4>
        <div className={`validation-result ${validation.is_valid ? 'valid' : 'invalid'}`}>
          <span className={`status-indicator ${validation.is_valid ? 'success' : 'error'}`}>
            {validation.is_valid ? '✓ Valid' : '✗ Invalid'}
          </span>
        </div>

        {validation.errors && validation.errors.length > 0 && (
          <div className="validation-errors">
            <h5>Errors:</h5>
            <ul>
              {validation.errors.map((error, index) => (
                <li key={index} className="error-item">{error}</li>
              ))}
            </ul>
          </div>
        )}

        {validation.warnings && validation.warnings.length > 0 && (
          <div className="validation-warnings">
            <h5>Warnings:</h5>
            <ul>
              {validation.warnings.map((warning, index) => (
                <li key={index} className="warning-item">{warning}</li>
              ))}
            </ul>
          </div>
        )}

        {validation.summary && (
          <div className="validation-summary">
            <h5>Content Summary:</h5>
            <div className="summary-grid">
              <div className="summary-item">
                <span className="summary-label">Has Metadata:</span>
                <span className={`summary-value ${validation.summary.has_metadata ? 'yes' : 'no'}`}>
                  {validation.summary.has_metadata ? 'Yes' : 'No'}
                </span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Has Database:</span>
                <span className={`summary-value ${validation.summary.has_database ? 'yes' : 'no'}`}>
                  {validation.summary.has_database ? `Yes (${validation.summary.database_statements} statements)` : 'No'}
                </span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Has State:</span>
                <span className={`summary-value ${validation.summary.has_state ? 'yes' : 'no'}`}>
                  {validation.summary.has_state ? `Yes (${validation.summary.state_modules.length} modules)` : 'No'}
                </span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Has Prompts:</span>
                <span className={`summary-value ${validation.summary.has_prompts ? 'yes' : 'no'}`}>
                  {validation.summary.has_prompts ? `Yes (${validation.summary.prompts_count} prompts)` : 'No'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderMetadataPreview = (metadata) => {
    if (!metadata || Object.keys(metadata).length === 0) return null;

    return (
      <div className="preview-section">
        <h4>Metadata</h4>
        <div className="metadata-grid">
          {metadata.name && (
            <div className="metadata-item">
              <span className="metadata-label">Name:</span>
              <span className="metadata-value">{metadata.name}</span>
            </div>
          )}
          {metadata.summary && (
            <div className="metadata-item">
              <span className="metadata-label">Summary:</span>
              <span className="metadata-value">{metadata.summary}</span>
            </div>
          )}
          {metadata.version && (
            <div className="metadata-item">
              <span className="metadata-label">Version:</span>
              <span className="metadata-value">{metadata.version}</span>
            </div>
          )}
          {metadata.author_name && (
            <div className="metadata-item">
              <span className="metadata-label">Author:</span>
              <span className="metadata-value">{metadata.author_name}</span>
            </div>
          )}
          {metadata.detailed_description && (
            <div className="metadata-item full-width">
              <span className="metadata-label">Description:</span>
              <span className="metadata-value">{metadata.detailed_description}</span>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderDatabasePreview = (databasePreview) => {
    if (!databasePreview || databasePreview.length === 0) return null;

    return (
      <div className="preview-section">
        <h4>Database Statements Preview</h4>
        <div className="database-preview">
          {databasePreview.map((statement, index) => (
            <div key={index} className="sql-statement">
              <span className="statement-number">{index + 1}.</span>
              <code className="sql-code">{statement}</code>
            </div>
          ))}
          {databasePreview.length === 5 && (
            <div className="preview-note">... and more statements</div>
          )}
        </div>
      </div>
    );
  };

  const renderStatePreview = (statePreview) => {
    if (!statePreview || Object.keys(statePreview).length === 0) return null;

    return (
      <div className="preview-section">
        <h4>State Modules Preview</h4>
        <div className="state-preview">
          {Object.entries(statePreview).map(([moduleName, moduleInfo]) => (
            <div key={moduleName} className="state-module">
              <h5 className="module-name">{moduleName}</h5>
              <div className="module-info">
                <span className="module-type">Type: {moduleInfo.type}</span>
                {moduleInfo.keys && (
                  <div className="module-keys">
                    <span>Keys: {moduleInfo.keys.join(', ')}</span>
                    {moduleInfo.total_keys > moduleInfo.keys.length && (
                      <span className="keys-more"> (+{moduleInfo.total_keys - moduleInfo.keys.length} more)</span>
                    )}
                  </div>
                )}
                {moduleInfo.value && (
                  <div className="module-value">
                    <span>Value: {moduleInfo.value}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderPromptsPreview = (promptsPreview) => {
    if (!promptsPreview || promptsPreview.length === 0) return null;

    return (
      <div className="preview-section">
        <h4>Prompts Preview</h4>
        <div className="prompts-preview">
          {promptsPreview.map((prompt, index) => (
            <div key={index} className="prompt-item">
              <h5 className="prompt-name">{prompt.name}</h5>
              <p className="prompt-description">{prompt.description}</p>
              <span className="prompt-length">Content length: {prompt.content_length} characters</span>
            </div>
          ))}
          {promptsPreview.length === 5 && (
            <div className="preview-note">... and more prompts</div>
          )}
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content preview-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Content Pack Preview: {filename}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {loading && (
            <div className="preview-loading">Loading preview...</div>
          )}

          {error && (
            <div className="preview-error">
              <p>Error loading preview: {error}</p>
              <button onClick={fetchPreview}>Retry</button>
            </div>
          )}

          {preview && (
            <div className="preview-content">
              {renderValidationStatus(preview.validation)}
              {renderMetadataPreview(preview.preview?.metadata)}
              {renderDatabasePreview(preview.preview?.database_preview)}
              {renderStatePreview(preview.preview?.state_preview)}
              {renderPromptsPreview(preview.preview?.prompts_preview)}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="modal-button secondary" onClick={onClose}>
            Close
          </button>
          {preview && preview.validation?.is_valid && (
            <button className="modal-button primary" onClick={handleLoadPack}>
              Load Content Pack
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ContentPackPreview;