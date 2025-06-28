import React, { useState, useEffect } from 'react';
import { 
  getAvailableContentPacks, 
  getLoadedContentPacks, 
  exportContentPack, 
  loadContentPack, 
  unloadContentPack, 
  clearAllLoadedPacks,
  getRemoteContentPacks,
  getRemoteRepositoryInfo,
  searchRemoteContentPacks,
  installRemoteContentPack,
  refreshRemoteCache,
  clearRemoteCache
} from '../api/client';
import ContentPackPreview from './ContentPackPreview';

const ContentPackManager = () => {
  const [availablePacks, setAvailablePacks] = useState([]);
  const [loadedPacks, setLoadedPacks] = useState([]);
  const [remotePacks, setRemotePacks] = useState([]);
  const [remoteRepositoryInfo, setRemoteRepositoryInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [remoteLoading, setRemoteLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('available');
  const [exportForm, setExportForm] = useState({
    filename: '',
    name: '',
    summary: '',
    description: '',
    authorName: '',
    authorEmail: ''
  });
  const [exportLoading, setExportLoading] = useState(false);
  const [exportMessage, setExportMessage] = useState('');
  const [actionLoading, setActionLoading] = useState({});
  const [actionMessage, setActionMessage] = useState('');
  const [previewModal, setPreviewModal] = useState({
    isOpen: false,
    filename: null
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedTags, setSelectedTags] = useState([]);

  useEffect(() => {
    fetchContentPacks();
    fetchRemoteRepositoryInfo();
  }, []);

  const fetchContentPacks = async () => {
    try {
      setLoading(true);
      const [availableResponse, loadedResponse] = await Promise.all([
        getAvailableContentPacks(),
        getLoadedContentPacks()
      ]);
      
      setAvailablePacks(availableResponse.data || []);
      setLoadedPacks(loadedResponse.data || []);
      setError(null);
    } catch (err) {
      setError('Failed to fetch content packs. Please ensure the core service is running.');
      console.error('Error fetching content packs:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRemoteContentPacks = async (forceRefresh = false) => {
    try {
      setRemoteLoading(true);
      const response = await getRemoteContentPacks(forceRefresh);
      setRemotePacks(response.data || []);
      setError(null);
    } catch (err) {
      setError('Failed to fetch remote content packs. Check your internet connection.');
      console.error('Error fetching remote content packs:', err);
    } finally {
      setRemoteLoading(false);
    }
  };

  const fetchRemoteRepositoryInfo = async () => {
    try {
      const response = await getRemoteRepositoryInfo();
      setRemoteRepositoryInfo(response.data);
    } catch (err) {
      console.error('Error fetching remote repository info:', err);
      setRemoteRepositoryInfo({ status: 'unavailable' });
    }
  };

  const handleSearchRemote = async () => {
    try {
      setRemoteLoading(true);
      const response = await searchRemoteContentPacks(searchQuery, selectedCategory, selectedTags);
      setRemotePacks(response.data || []);
      setError(null);
    } catch (err) {
      setError('Failed to search remote content packs.');
      console.error('Error searching remote content packs:', err);
    } finally {
      setRemoteLoading(false);
    }
  };

  const handleInstallRemotePack = async (filename, loadImmediately = true) => {
    setActionLoading({...actionLoading, [filename]: true});
    setActionMessage('');

    try {
      const response = await installRemoteContentPack(filename, loadImmediately);
      setActionMessage(`✓ ${response.data.message}`);
      
      // Refresh both local and remote packs
      fetchContentPacks();
      fetchRemoteContentPacks();
    } catch (err) {
      setActionMessage(`✗ Install failed: ${err.response?.data?.detail || err.message}`);
      console.error('Install error:', err);
    } finally {
      setActionLoading({...actionLoading, [filename]: false});
      setTimeout(() => setActionMessage(''), 3000);
    }
  };

  const handleRefreshRemoteCache = async () => {
    try {
      setRemoteLoading(true);
      await refreshRemoteCache();
      await fetchRemoteContentPacks(true);
      setActionMessage('✓ Remote cache refreshed successfully');
    } catch (err) {
      setActionMessage(`✗ Failed to refresh cache: ${err.response?.data?.detail || err.message}`);
      console.error('Cache refresh error:', err);
    } finally {
      setRemoteLoading(false);
      setTimeout(() => setActionMessage(''), 3000);
    }
  };

  const handleClearRemoteCache = async () => {
    try {
      await clearRemoteCache();
      setRemotePacks([]);
      setActionMessage('✓ Remote cache cleared successfully');
    } catch (err) {
      setActionMessage(`✗ Failed to clear cache: ${err.response?.data?.detail || err.message}`);
      console.error('Cache clear error:', err);
    } finally {
      setTimeout(() => setActionMessage(''), 3000);
    }
  };

  const handleExport = async (e) => {
    e.preventDefault();
    setExportLoading(true);
    setExportMessage('');

    try {
      const metadata = {
        name: exportForm.name,
        summary: exportForm.summary,
        detailed_description: exportForm.description,
        author_name: exportForm.authorName,
        author_email: exportForm.authorEmail
      };

      const response = await exportContentPack(exportForm.filename, metadata);
      setExportMessage(`✓ ${response.data.message}`);
      
      // Reset form
      setExportForm({
        filename: '',
        name: '',
        summary: '',
        description: '',
        authorName: '',
        authorEmail: ''
      });

      // Refresh the available packs list
      fetchContentPacks();
    } catch (err) {
      setExportMessage(`✗ Export failed: ${err.response?.data?.detail || err.message}`);
      console.error('Export error:', err);
    } finally {
      setExportLoading(false);
    }
  };

  const handleLoadPack = async (filename) => {
    setActionLoading({...actionLoading, [filename]: true});
    setActionMessage('');

    try {
      const response = await loadContentPack(filename);
      setActionMessage(`✓ ${response.data.message}`);
      
      // Refresh the packs list
      fetchContentPacks();
    } catch (err) {
      setActionMessage(`✗ Load failed: ${err.response?.data?.detail || err.message}`);
      console.error('Load error:', err);
    } finally {
      setActionLoading({...actionLoading, [filename]: false});
      // Clear message after 3 seconds
      setTimeout(() => setActionMessage(''), 3000);
    }
  };

  const handleUnloadPack = async (identifier) => {
    setActionLoading({...actionLoading, [identifier]: true});
    setActionMessage('');

    try {
      const response = await unloadContentPack(identifier);
      setActionMessage(`✓ ${response.data.message}`);
      
      // Refresh the packs list
      fetchContentPacks();
    } catch (err) {
      setActionMessage(`✗ Unload failed: ${err.response?.data?.detail || err.message}`);
      console.error('Unload error:', err);
    } finally {
      setActionLoading({...actionLoading, [identifier]: false});
      // Clear message after 3 seconds
      setTimeout(() => setActionMessage(''), 3000);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Are you sure you want to clear all loaded content packs from tracking? This will not revert state or database changes.')) {
      return;
    }

    setActionLoading({...actionLoading, 'clear-all': true});
    setActionMessage('');

    try {
      const response = await clearAllLoadedPacks();
      setActionMessage(`✓ ${response.data.message}`);
      
      // Refresh the packs list
      fetchContentPacks();
    } catch (err) {
      setActionMessage(`✗ Clear failed: ${err.response?.data?.detail || err.message}`);
      console.error('Clear error:', err);
    } finally {
      setActionLoading({...actionLoading, 'clear-all': false});
      // Clear message after 3 seconds
      setTimeout(() => setActionMessage(''), 3000);
    }
  };

  const isPackLoaded = (filename) => {
    return loadedPacks.some(pack => {
      const packFilename = pack.path ? pack.path.split('/').pop() : '';
      return packFilename === filename;
    });
  };

  const handlePreviewPack = (filename) => {
    setPreviewModal({
      isOpen: true,
      filename: filename
    });
  };

  const handleClosePreview = () => {
    setPreviewModal({
      isOpen: false,
      filename: null
    });
  };

  const handleLoadFromPreview = (filename) => {
    handleLoadPack(filename);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const renderAvailablePacks = () => (
    <div className="content-pack-list">
      <h3>Available Content Packs</h3>
      {actionMessage && (
        <div className={`action-message ${actionMessage.startsWith('✓') ? 'success' : 'error'}`}>
          {actionMessage}
        </div>
      )}
      {availablePacks.length === 0 ? (
        <p>No content packs found in the content_packs directory.</p>
      ) : (
        <div className="pack-grid">
          {availablePacks.map((pack, index) => {
            const isLoaded = isPackLoaded(pack.filename);
            const isLoading = actionLoading[pack.filename];
            
            return (
              <div key={index} className={`pack-card ${isLoaded ? 'loaded' : ''}`}>
                <div className="pack-header">
                  <h4>{pack.metadata?.name || pack.filename}</h4>
                  <div className="pack-status">
                    <span className="pack-filename">{pack.filename}</span>
                    {isLoaded && <span className="loaded-badge">Loaded</span>}
                  </div>
                </div>
                
                <div className="pack-content">
                  {pack.metadata?.summary && (
                    <p className="pack-summary">{pack.metadata.summary}</p>
                  )}
                  
                  <div className="pack-features">
                    {pack.has_database && <span className="feature-badge database">Database</span>}
                    {pack.has_state && <span className="feature-badge state">State</span>}
                    {pack.has_prompts && <span className="feature-badge prompts">Prompts</span>}
                  </div>
                  
                  {pack.metadata?.author_name && (
                    <p className="pack-author">By: {pack.metadata.author_name}</p>
                  )}
                  
                  {pack.metadata?.version && (
                    <p className="pack-version">Version: {pack.metadata.version}</p>
                  )}
                  
                  <div className="pack-actions">
                    <div className="action-buttons">
                      {!isLoaded ? (
                        <button 
                          className="load-button"
                          onClick={() => handleLoadPack(pack.filename)}
                          disabled={isLoading}
                        >
                          {isLoading ? 'Loading...' : 'Load Pack'}
                        </button>
                      ) : (
                        <button 
                          className="unload-button"
                          onClick={() => handleUnloadPack(pack.filename)}
                          disabled={isLoading}
                        >
                          {isLoading ? 'Unloading...' : 'Unload Pack'}
                        </button>
                      )}
                      <button 
                        className="preview-button"
                        onClick={() => handlePreviewPack(pack.filename)}
                        disabled={isLoading}
                      >
                        Preview
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  const renderLoadedPacks = () => (
    <div className="content-pack-list">
      <div className="loaded-packs-header">
        <h3>Currently Loaded Content Packs</h3>
        {loadedPacks.length > 0 && (
          <button 
            className="clear-all-button"
            onClick={handleClearAll}
            disabled={actionLoading['clear-all']}
          >
            {actionLoading['clear-all'] ? 'Clearing...' : 'Clear All'}
          </button>
        )}
      </div>
      
      {actionMessage && (
        <div className={`action-message ${actionMessage.startsWith('✓') ? 'success' : 'error'}`}>
          {actionMessage}
        </div>
      )}
      
      {loadedPacks.length === 0 ? (
        <p>No content packs are currently loaded.</p>
      ) : (
        <div className="pack-grid">
          {loadedPacks.map((pack, index) => {
            const packFilename = pack.filename || (pack.path ? pack.path.split('/').pop() : '');
            const isLoading = actionLoading[packFilename] || actionLoading[pack.metadata?.name];
            
            return (
              <div key={index} className="pack-card loaded">
                <div className="pack-header">
                  <h4>{pack.metadata?.name || 'Unnamed Pack'}</h4>
                  <span className="loaded-badge">Loaded</span>
                </div>
                
                <div className="pack-content">
                  {pack.metadata?.summary && (
                    <p className="pack-summary">{pack.metadata.summary}</p>
                  )}
                  
                  <p className="pack-loaded-time">
                    Loaded: {formatDate(pack.loaded_at)}
                  </p>
                  
                  {pack.path && (
                    <p className="pack-path">Path: {pack.path}</p>
                  )}
                  
                  <div className="pack-actions">
                    <div className="action-buttons">
                      <button 
                        className="unload-button"
                        onClick={() => handleUnloadPack(packFilename)}
                        disabled={isLoading}
                      >
                        {isLoading ? 'Unloading...' : 'Unload Pack'}
                      </button>
                      <button 
                        className="preview-button"
                        onClick={() => handlePreviewPack(packFilename)}
                        disabled={isLoading || !packFilename}
                      >
                        Preview
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  const renderRemotePacks = () => {
    const getUniqueCategories = () => {
      const categories = remotePacks.map(pack => pack.category).filter(Boolean);
      return [...new Set(categories)];
    };

    const getUniqueTags = () => {
      const allTags = remotePacks.flatMap(pack => pack.tags || []);
      return [...new Set(allTags)];
    };

    return (
      <div className="content-pack-list">
        <div className="remote-packs-header">
          <h3>Remote Content Packs</h3>
          <div className="remote-controls">
            <button 
              onClick={() => fetchRemoteContentPacks(true)}
              disabled={remoteLoading}
              className="refresh-button"
            >
              {remoteLoading ? 'Loading...' : 'Refresh'}
            </button>
            <button 
              onClick={handleRefreshRemoteCache}
              disabled={remoteLoading}
              className="cache-button"
            >
              Refresh Cache
            </button>
            <button 
              onClick={handleClearRemoteCache}
              className="cache-button"
            >
              Clear Cache
            </button>
          </div>
        </div>

        {remoteRepositoryInfo && (
          <div className="repository-info">
            <p>
              <strong>Repository Status:</strong> {remoteRepositoryInfo.status}
              {remoteRepositoryInfo.statistics && (
                <span> | {remoteRepositoryInfo.statistics.total_packs} packs available</span>
              )}
            </p>
          </div>
        )}

        <div className="search-controls">
          <div className="search-row">
            <input
              type="text"
              placeholder="Search content packs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="category-select"
            >
              <option value="">All Categories</option>
              {getUniqueCategories().map(category => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
            <button 
              onClick={handleSearchRemote}
              disabled={remoteLoading}
              className="search-button"
            >
              Search
            </button>
            <button 
              onClick={() => {
                setSearchQuery('');
                setSelectedCategory('');
                setSelectedTags([]);
                fetchRemoteContentPacks();
              }}
              className="clear-search-button"
            >
              Clear
            </button>
          </div>
        </div>

        {actionMessage && (
          <div className={`action-message ${actionMessage.startsWith('✓') ? 'success' : 'error'}`}>
            {actionMessage}
          </div>
        )}

        {remoteLoading ? (
          <div className="loading-message">Loading remote content packs...</div>
        ) : remotePacks.length === 0 ? (
          <p>No remote content packs found. Check your internet connection or try refreshing.</p>
        ) : (
          <div className="pack-grid">
            {remotePacks.map((pack, index) => {
              const isInstalled = availablePacks.some(localPack => localPack.filename === pack.filename);
              const isLoading = actionLoading[pack.filename];
              
              return (
                <div key={index} className={`pack-card remote ${isInstalled ? 'installed' : ''}`}>
                  <div className="pack-header">
                    <h4>{pack.name || pack.filename}</h4>
                    <div className="pack-status">
                      <span className="pack-filename">{pack.filename}</span>
                      <span className="source-badge remote">Remote</span>
                      {isInstalled && <span className="installed-badge">Installed</span>}
                    </div>
                  </div>
                  
                  <div className="pack-content">
                    {pack.summary && (
                      <p className="pack-summary">{pack.summary}</p>
                    )}
                    
                    <div className="pack-features">
                      {pack.sections?.has_database && <span className="feature-badge database">Database</span>}
                      {pack.sections?.has_state && <span className="feature-badge state">State</span>}
                      {pack.sections?.has_prompts && <span className="feature-badge prompts">Prompts</span>}
                    </div>
                    
                    {pack.category && (
                      <p className="pack-category">Category: {pack.category}</p>
                    )}
                    
                    {pack.tags && pack.tags.length > 0 && (
                      <div className="pack-tags">
                        {pack.tags.map(tag => (
                          <span key={tag} className="tag-badge">{tag}</span>
                        ))}
                      </div>
                    )}
                    
                    {pack.author_name && (
                      <p className="pack-author">By: {pack.author_name}</p>
                    )}
                    
                    {pack.version && (
                      <p className="pack-version">Version: {pack.version}</p>
                    )}
                    
                    {pack.file_size_bytes && (
                      <p className="pack-size">Size: {(pack.file_size_bytes / 1024).toFixed(1)} KB</p>
                    )}
                    
                    <div className="pack-actions">
                      <div className="action-buttons">
                        {!isInstalled ? (
                          <>
                            <button 
                              className="install-button primary"
                              onClick={() => handleInstallRemotePack(pack.filename, true)}
                              disabled={isLoading}
                            >
                              {isLoading ? 'Installing...' : 'Install & Load'}
                            </button>
                            <button 
                              className="install-button secondary"
                              onClick={() => handleInstallRemotePack(pack.filename, false)}
                              disabled={isLoading}
                            >
                              Install Only
                            </button>
                          </>
                        ) : (
                          <span className="installed-text">Already Installed</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const renderExportForm = () => (
    <div className="export-form-container">
      <h3>Export Current State as Content Pack</h3>
      <form onSubmit={handleExport} className="export-form">
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="filename">Filename:</label>
            <input
              type="text"
              id="filename"
              value={exportForm.filename}
              onChange={(e) => setExportForm({...exportForm, filename: e.target.value})}
              placeholder="my-content-pack.json"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="name">Pack Name:</label>
            <input
              type="text"
              id="name"
              value={exportForm.name}
              onChange={(e) => setExportForm({...exportForm, name: e.target.value})}
              placeholder="My Custom Content Pack"
            />
          </div>

          <div className="form-group">
            <label htmlFor="summary">Summary:</label>
            <input
              type="text"
              id="summary"
              value={exportForm.summary}
              onChange={(e) => setExportForm({...exportForm, summary: e.target.value})}
              placeholder="Brief description of this content pack"
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="description">Detailed Description:</label>
          <textarea
            id="description"
            value={exportForm.description}
            onChange={(e) => setExportForm({...exportForm, description: e.target.value})}
            placeholder="Detailed description of what this content pack contains..."
            rows="3"
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="authorName">Author Name:</label>
            <input
              type="text"
              id="authorName"
              value={exportForm.authorName}
              onChange={(e) => setExportForm({...exportForm, authorName: e.target.value})}
              placeholder="Your Name"
            />
          </div>

          <div className="form-group">
            <label htmlFor="authorEmail">Author Email:</label>
            <input
              type="email"
              id="authorEmail"
              value={exportForm.authorEmail}
              onChange={(e) => setExportForm({...exportForm, authorEmail: e.target.value})}
              placeholder="your.email@example.com"
            />
          </div>
          
          <div className="form-group">
            <label>&nbsp;</label>
            <button type="submit" disabled={exportLoading || !exportForm.filename}>
              {exportLoading ? 'Exporting...' : 'Export Content Pack'}
            </button>
          </div>
        </div>


        {exportMessage && (
          <div className={`export-message ${exportMessage.startsWith('✓') ? 'success' : 'error'}`}>
            {exportMessage}
          </div>
        )}
      </form>
    </div>
  );

  if (loading) {
    return <div className="content-pack-manager loading">Loading content packs...</div>;
  }

  if (error) {
    return (
      <div className="content-pack-manager error">
        <p className="error-message">{error}</p>
        <button onClick={fetchContentPacks}>Retry</button>
      </div>
    );
  }

  return (
    <div className="content-pack-manager">
      <div className="content-pack-header">
        <h2>Content Pack Manager</h2>
        <button onClick={fetchContentPacks} className="refresh-button">
          Refresh
        </button>
      </div>

      <div className="content-pack-tabs">
        <button 
          className={`tab ${activeTab === 'available' ? 'active' : ''}`}
          onClick={() => setActiveTab('available')}
        >
          Local ({availablePacks.length})
        </button>
        <button 
          className={`tab ${activeTab === 'remote' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('remote');
            if (remotePacks.length === 0) {
              fetchRemoteContentPacks();
            }
          }}
        >
          Remote ({remotePacks.length})
        </button>
        <button 
          className={`tab ${activeTab === 'loaded' ? 'active' : ''}`}
          onClick={() => setActiveTab('loaded')}
        >
          Loaded ({loadedPacks.length})
        </button>
        <button 
          className={`tab ${activeTab === 'export' ? 'active' : ''}`}
          onClick={() => setActiveTab('export')}
        >
          Export
        </button>
      </div>

      <div className="content-pack-content">
        {activeTab === 'available' && renderAvailablePacks()}
        {activeTab === 'remote' && renderRemotePacks()}
        {activeTab === 'loaded' && renderLoadedPacks()}
        {activeTab === 'export' && renderExportForm()}
      </div>

      {/* Preview Modal */}
      <ContentPackPreview
        filename={previewModal.filename}
        isOpen={previewModal.isOpen}
        onClose={handleClosePreview}
        onLoad={handleLoadFromPreview}
      />
    </div>
  );
};

export default ContentPackManager;