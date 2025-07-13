import React, { useState, useEffect } from 'react';
import { getModulesStatus, getCategories, getModulesByCategory, toggleModule, toggleTool, toggleCategory, getMcpServers } from '../api/client';
import './SettingsPage.css';

const SettingsPage = () => {
  const [modules, setModules] = useState({});
  const [categories, setCategories] = useState({});
  const [modulesByCategory, setModulesByCategory] = useState({});
  const [mcpServers, setMcpServers] = useState({ servers: [], stats: {} });
  const [loading, setLoading] = useState(true);
  const [mcpLoading, setMcpLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [toggleLoading, setToggleLoading] = useState({});
  const [toolToggleLoading, setToolToggleLoading] = useState({});
  const [categoryToggleLoading, setCategoryToggleLoading] = useState({});

  useEffect(() => {
    loadModulesStatus();
    loadCategoriesAndModules();
    loadMcpServers();
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

  const loadCategoriesAndModules = async () => {
    try {
      const [categoriesResponse, modulesByCategoryResponse] = await Promise.all([
        getCategories(),
        getModulesByCategory()
      ]);
      
      setCategories(categoriesResponse.data.categories);
      setModulesByCategory(modulesByCategoryResponse.data.modules_by_category);
    } catch (err) {
      console.error('Failed to load categories:', err);
      // Don't set error here as modules might still work
    }
  };

  const loadMcpServers = async () => {
    try {
      setMcpLoading(true);
      const response = await getMcpServers();
      if (response.data && response.data.data) {
        setMcpServers(response.data.data);
      }
    } catch (err) {
      console.error('Failed to load MCP servers:', err);
      // Don't set error for MCP servers as it's not critical
    } finally {
      setMcpLoading(false);
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

  const handleCategoryToggle = async (categoryName) => {
    setCategoryToggleLoading(prev => ({ ...prev, [categoryName]: true }));
    try {
      await toggleCategory(categoryName);
      // Reload categories and modules to get updated state
      await loadCategoriesAndModules();
    } catch (err) {
      console.error(`Failed to toggle category ${categoryName}:`, err);
      alert(`Failed to toggle category ${categoryName}. Please try again.`);
    } finally {
      setCategoryToggleLoading(prev => ({ ...prev, [categoryName]: false }));
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
        {/* Category Management Section */}
        {Object.keys(categories).length > 0 && (
          <div className="settings-section">
            <h2>Category Management</h2>
            <p>Enable or disable entire categories of modules. Disabled categories will not appear in the dashboard.</p>
            
            <div className="categories-grid">
              {Object.entries(categories)
                .sort((a, b) => a[1].sort_order - b[1].sort_order)
                .map(([categoryName, categoryInfo]) => (
                  <div key={categoryName} className="category-item">
                    <div className="category-header">
                      <h3>{categoryInfo.display_name}</h3>
                      <label className="toggle-switch">
                        <input
                          type="checkbox"
                          checked={categoryInfo.is_enabled}
                          onChange={() => handleCategoryToggle(categoryName)}
                          disabled={categoryToggleLoading[categoryName] || categoryName === 'productivity'}
                        />
                        <span className="slider"></span>
                      </label>
                    </div>
                    <p className="category-description">{categoryInfo.description}</p>
                    <div className="category-stats">
                      <span className="module-count">
                        {categoryInfo.module_count} module{categoryInfo.module_count !== 1 ? 's' : ''}
                      </span>
                      {categoryName === 'productivity' && (
                        <span className="category-note">(Always enabled)</span>
                      )}
                    </div>
                    {categoryToggleLoading[categoryName] && (
                      <div className="loading-indicator">Updating...</div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        )}

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

        <div className="settings-section">
          <h2>MCP Servers</h2>
          <p className="section-description">
            External MCP (Model Context Protocol) servers that provide additional tools and capabilities.
            These servers are discovered automatically and their tools are made available through the proxy.
          </p>
          
          {mcpLoading ? (
            <div className="loading-state">
              <p>Loading MCP servers...</p>
            </div>
          ) : (
            <>
              {mcpServers.stats && (
                <div className="mcp-stats">
                  <div className="stat-item">
                    <span className="stat-label">Total Servers:</span>
                    <span className="stat-value">{mcpServers.stats.total_servers || 0}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Connected:</span>
                    <span className="stat-value">{mcpServers.stats.connected_servers || 0}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Total Tools:</span>
                    <span className="stat-value">{mcpServers.stats.total_tools || 0}</span>
                  </div>
                </div>
              )}

              <div className="mcp-servers-list">
                {mcpServers.servers && mcpServers.servers.length > 0 ? (
                  mcpServers.servers.map((server, index) => (
                    <div key={server.name || index} className="mcp-server-item">
                      <div className="server-header">
                        <div className="server-info">
                          <span className="server-name">{server.name || `Server ${index + 1}`}</span>
                          <span className={`server-status ${server.connected ? 'connected' : 'disconnected'}`}>
                            {server.connected ? 'Connected' : 'Disconnected'}
                          </span>
                        </div>
                        <div className="server-meta">
                          <span className="tools-count">{server.tools_count || 0} tools</span>
                        </div>
                      </div>
                      
                      {server.tools && server.tools.length > 0 && (
                        <div className="mcp-tools-section">
                          <h4>Available Tools</h4>
                          <div className="mcp-tools-list">
                            {server.tools.map((tool, toolIndex) => (
                              <div key={tool.name || toolIndex} className="mcp-tool-item">
                                <div className="mcp-tool-info">
                                  <span className="mcp-tool-name">{tool.display_name || tool.name}</span>
                                  <span className="mcp-tool-description">{tool.description || 'No description available'}</span>
                                </div>
                                <div className="mcp-tool-status">
                                  <span className="status-indicator available">Available</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="no-mcp-servers">
                    <p>No MCP servers configured or discovered.</p>
                    <p className="help-text">
                      MCP servers can be configured in the proxy configuration file to extend functionality with external tools.
                    </p>
                  </div>
                )}
              </div>
            </>
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