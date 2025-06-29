import React, { useState, useEffect } from 'react';
import { getModulesStatus, toggleModule } from '../api/client';

const SettingsPage = () => {
  const [modules, setModules] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [toggleLoading, setToggleLoading] = useState({});

  useEffect(() => {
    loadModulesStatus();
  }, []);

  const loadModulesStatus = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      const response = await getModulesStatus();
      setModules(response.data.modules);
      setError(null);
    } catch (err) {
      console.error('Failed to load modules status:', err);
      setError('Failed to load modules status');
    } finally {
      if (isRefresh) {
        setRefreshing(false);
      } else {
        setLoading(false);
      }
    }
  };

  const handleModuleToggle = async (moduleName, currentEnabled) => {
    const newEnabled = !currentEnabled;
    
    try {
      setToggleLoading(prev => ({ ...prev, [moduleName]: true }));
      
      await toggleModule(moduleName, newEnabled);
      
      // Update local state
      setModules(prev => ({
        ...prev,
        [moduleName]: {
          ...prev[moduleName],
          is_enabled: newEnabled,
          is_loaded: newEnabled // Assume it gets loaded/unloaded immediately
        }
      }));
      
      setError(null);
    } catch (err) {
      console.error(`Failed to toggle module ${moduleName}:`, err);
      setError(`Failed to ${newEnabled ? 'enable' : 'disable'} module ${moduleName}`);
    } finally {
      setToggleLoading(prev => ({ ...prev, [moduleName]: false }));
    }
  };

  const handleCancel = () => {
    // Navigate back to dashboard
    window.history.back();
  };

  if (loading) {
    return (
      <div className="settings-container">
        <h1>Settings</h1>
        <div className="loading">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="settings-container">
      <h1>Settings</h1>
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      <div className="settings-form">
        <div className="settings-section">
          <h2>Module Configuration</h2>
          <p>Enable or disable modules to control which tools are available in the system.</p>
          
          <div className="modules-list">
            {Object.entries(modules).map(([moduleName, moduleInfo]) => (
              <div key={moduleName} className="module-item">
                <div className="module-info">
                  <div className="module-header">
                    <h3>{moduleInfo.display_name}</h3>
                    <div className="module-status">
                      <span className={`status-indicator ${moduleInfo.is_loaded ? 'loaded' : 'unloaded'}`}>
                        {moduleInfo.is_loaded ? 'Loaded' : 'Unloaded'}
                      </span>
                    </div>
                  </div>
                  <p className="module-description">{moduleInfo.description}</p>
                </div>
                <div className="module-controls">
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={moduleInfo.is_enabled}
                      onChange={() => handleModuleToggle(moduleName, moduleInfo.is_enabled)}
                      disabled={toggleLoading[moduleName]}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                  {toggleLoading[moduleName] && (
                    <span className="toggle-loading">Updating...</span>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          {Object.keys(modules).length === 0 && (
            <p className="no-modules">No modules found.</p>
          )}
        </div>
        
        <div className="settings-section">
          <h2>Future Tool-Level Configuration</h2>
          <p className="future-feature">
            In the next release, you'll be able to enable/disable individual tools within each module.
            This will provide fine-grained control over which specific functions are available.
          </p>
        </div>
      </div>
      
      <div className="settings-actions">
        <button className="cancel-button" onClick={handleCancel}>Back to Dashboard</button>
        <button className="refresh-button" onClick={() => loadModulesStatus(true)} disabled={refreshing}>
          {refreshing ? 'Refreshing...' : 'Refresh Status'}
        </button>
      </div>
    </div>
  );
};

export default SettingsPage;