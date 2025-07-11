import React, { useState, useEffect } from 'react';
import { getModulesStatus, toggleModule, toggleTool } from '../api/client';

const SettingsPage = () => {
  const [modules, setModules] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [toggleLoading, setToggleLoading] = useState({});
  const [toolToggleLoading, setToolToggleLoading] = useState({});

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

  const handleToolToggle = async (moduleName, toolName, currentEnabled) => {
    const newEnabled = !currentEnabled;
    const toolKey = `${moduleName}.${toolName}`;
    
    try {
      setToolToggleLoading(prev => ({ ...prev, [toolKey]: true }));
      
      await toggleTool(moduleName, toolName, newEnabled);
      
      // Update local state
      setModules(prev => ({
        ...prev,
        [moduleName]: {
          ...prev[moduleName],
          tools: {
            ...prev[moduleName].tools,
            [toolName]: {
              ...prev[moduleName].tools[toolName],
              is_enabled: newEnabled
            }
          }
        }
      }));
      
      setError(null);
    } catch (err) {
      console.error(`Failed to toggle tool ${moduleName}.${toolName}:`, err);
      setError(`Failed to ${newEnabled ? 'enable' : 'disable'} tool ${moduleName}.${toolName}`);
    } finally {
      setToolToggleLoading(prev => ({ ...prev, [toolKey]: false }));
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
                
                {/* Tool-level configuration */}
                {moduleInfo.is_enabled && moduleInfo.tools && Object.keys(moduleInfo.tools).length > 0 && (
                  <div className="tools-section">
                    <h4>Individual Tools</h4>
                    <div className="tools-list">
                      {Object.entries(moduleInfo.tools).map(([toolName, toolInfo]) => (
                        <div key={toolName} className="tool-item">
                          <div className="tool-info">
                            <span className="tool-name">{toolInfo.display_name}</span>
                            <span className="tool-description">{toolInfo.description}</span>
                          </div>
                          <div className="tool-controls">
                            <label className="toggle-switch tool-toggle">
                              <input
                                type="checkbox"
                                checked={toolInfo.is_enabled}
                                onChange={() => handleToolToggle(moduleName, toolName, toolInfo.is_enabled)}
                                disabled={toolToggleLoading[`${moduleName}.${toolName}`]}
                              />
                              <span className="toggle-slider"></span>
                            </label>
                            {toolToggleLoading[`${moduleName}.${toolName}`] && (
                              <span className="toggle-loading">Updating...</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
          
          {Object.keys(modules).length === 0 && (
            <p className="no-modules">No modules found.</p>
          )}
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