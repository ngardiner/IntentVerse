import React, { useState, useEffect } from 'react';
import { getPackVariables, setPackVariable, resetPackVariable, resetAllPackVariables, previewContentPack } from '../api/client';

const VariableManager = ({ packName, packFilename, isOpen, onClose }) => {
  const [variables, setVariables] = useState({});
  const [packDefaults, setPackDefaults] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingVariable, setEditingVariable] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // Load variables when component opens
  useEffect(() => {
    if (isOpen && packName && packFilename) {
      loadPackData();
    }
  }, [isOpen, packName, packFilename]);

  const loadPackData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Load both user variables and pack defaults
      const [variablesResponse, previewResponse] = await Promise.all([
        getPackVariables(packName),
        previewContentPack(packFilename)
      ]);
      
      setVariables(variablesResponse.data.variables || {});
      
      // Extract pack defaults from preview
      const contentPack = previewResponse.data.content_pack;
      setPackDefaults(contentPack?.variables || {});
    } catch (err) {
      console.error('Error loading pack data:', err);
      setError(err.response?.data?.detail || 'Failed to load pack data');
    } finally {
      setLoading(false);
    }
  };

  const loadVariables = async () => {
    try {
      const response = await getPackVariables(packName);
      setVariables(response.data.variables || {});
    } catch (err) {
      console.error('Error loading variables:', err);
      setError(err.response?.data?.detail || 'Failed to load variables');
    }
  };

  const handleEditVariable = (variableName, currentValue) => {
    setEditingVariable(variableName);
    setEditValue(currentValue || '');
    setError(null);
    setSuccessMessage('');
  };

  const handleSaveVariable = async () => {
    if (!editingVariable) return;

    setSaving(true);
    setError(null);
    try {
      await setPackVariable(packName, editingVariable, editValue);
      
      // Update local state
      setVariables(prev => ({
        ...prev,
        [editingVariable]: editValue
      }));
      
      setEditingVariable(null);
      setEditValue('');
      setSuccessMessage(`Variable '${editingVariable}' updated successfully`);
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      console.error('Error saving variable:', err);
      setError(err.response?.data?.detail || 'Failed to save variable');
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingVariable(null);
    setEditValue('');
    setError(null);
  };

  const handleResetVariable = async (variableName) => {
    if (!window.confirm(`Are you sure you want to reset '${variableName}' to its default value?`)) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await resetPackVariable(packName, variableName);
      
      // Reload variables to get the default value
      await loadVariables();
      
      setSuccessMessage(`Variable '${variableName}' reset to default value`);
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      console.error('Error resetting variable:', err);
      setError(err.response?.data?.detail || 'Failed to reset variable');
    } finally {
      setSaving(false);
    }
  };

  const handleResetAllVariables = async () => {
    if (!window.confirm('Are you sure you want to reset ALL variables to their default values? This cannot be undone.')) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await resetAllPackVariables(packName);
      
      // Reload variables to get the default values
      await loadVariables();
      
      setSuccessMessage('All variables reset to default values');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      console.error('Error resetting all variables:', err);
      setError(err.response?.data?.detail || 'Failed to reset all variables');
    } finally {
      setSaving(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSaveVariable();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content variable-manager-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Manage Variables: {packName}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          {loading && (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Loading variables...</p>
            </div>
          )}

          {error && (
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
          )}

          {successMessage && (
            <div className="success-message">
              <strong>Success:</strong> {successMessage}
            </div>
          )}

          {!loading && Object.keys(packDefaults).length === 0 && (
            <div className="no-variables">
              <p>This content pack does not define any variables.</p>
              <p>Variables allow customization of content pack values and can be defined in the content pack's JSON structure.</p>
            </div>
          )}

          {!loading && Object.keys(packDefaults).length > 0 && (
            <div className="variables-container">
              <div className="variables-header">
                <h4>Variables ({Object.keys(packDefaults).length})</h4>
                <div className="variables-actions">
                  {Object.keys(variables).length > 0 && (
                    <button 
                      className="reset-all-button"
                      onClick={handleResetAllVariables}
                      disabled={saving}
                    >
                      Reset All to Defaults
                    </button>
                  )}
                </div>
              </div>

              <div className="variables-info">
                <p>
                  <strong>Variables</strong> allow you to customize content pack values. 
                  Changes are saved automatically and apply to all prompts and content in this pack.
                </p>
                <div className="variables-stats">
                  <span className="stat">
                    <strong>{Object.keys(packDefaults).length}</strong> total variables
                  </span>
                  <span className="stat">
                    <strong>{Object.keys(variables).length}</strong> customized
                  </span>
                </div>
              </div>

              <div className="variables-list">
                {Object.keys(packDefaults).map((variableName) => {
                  const defaultValue = packDefaults[variableName];
                  const userValue = variables[variableName];
                  const effectiveValue = userValue !== undefined ? userValue : defaultValue;
                  const isCustomized = userValue !== undefined;
                  
                  return (
                  <div key={variableName} className="variable-row">
                    <div className="variable-info">
                      <div className="variable-name-section">
                        <span className="variable-token">{{variableName}}</span>
                        <span className="variable-name">{variableName}</span>
                        {isCustomized && <span className="customized-badge">Custom</span>}
                      </div>
                      
                      <div className="variable-value-section">
                        {editingVariable === variableName ? (
                          <div className="variable-edit">
                            <input
                              type="text"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onKeyPress={handleKeyPress}
                              className="variable-input"
                              placeholder="Enter variable value"
                              autoFocus
                              disabled={saving}
                            />
                            <div className="edit-actions">
                              <button 
                                className="save-button"
                                onClick={handleSaveVariable}
                                disabled={saving || !editValue.trim()}
                              >
                                {saving ? 'Saving...' : 'Save'}
                              </button>
                              <button 
                                className="cancel-button"
                                onClick={handleCancelEdit}
                                disabled={saving}
                              >
                                Cancel
                              </button>
                            </div>
                            {defaultValue && (
                              <div className="default-reference">
                                <span className="default-label">Default:</span>
                                <span className="default-value">{defaultValue}</span>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="variable-display">
                            <div className="current-value">
                              <span className="value-label">Current:</span>
                              <span className={`variable-current-value ${isCustomized ? 'customized' : 'default'}`}>
                                {effectiveValue || <em>No value set</em>}
                              </span>
                            </div>
                            {isCustomized && defaultValue !== effectiveValue && (
                              <div className="default-value">
                                <span className="value-label">Default:</span>
                                <span className="variable-default-value">{defaultValue}</span>
                              </div>
                            )}
                            <div className="variable-actions">
                              <button 
                                className="edit-button"
                                onClick={() => handleEditVariable(variableName, effectiveValue)}
                                disabled={saving}
                              >
                                Edit
                              </button>
                              {isCustomized && (
                                <button 
                                  className="reset-button"
                                  onClick={() => handleResetVariable(variableName)}
                                  disabled={saving}
                                  title="Reset to default value"
                                >
                                  Reset
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <div className="footer-info">
            <p>
              <strong>Tip:</strong> Variable changes apply immediately to all content in this pack. 
              Use the token format <code>{{variable_name}}</code> in prompts to reference variables.
            </p>
          </div>
          <div className="footer-actions">
            <button className="modal-button secondary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VariableManager;