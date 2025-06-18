import React, { useState, useEffect } from 'react';
import { getAvailableContentPacks, getLoadedContentPacks, exportContentPack } from '../api/client';

const ContentPackManager = () => {
  const [availablePacks, setAvailablePacks] = useState([]);
  const [loadedPacks, setLoadedPacks] = useState([]);
  const [loading, setLoading] = useState(true);
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

  useEffect(() => {
    fetchContentPacks();
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
      {availablePacks.length === 0 ? (
        <p>No content packs found in the content_packs directory.</p>
      ) : (
        <div className="pack-grid">
          {availablePacks.map((pack, index) => (
            <div key={index} className="pack-card">
              <div className="pack-header">
                <h4>{pack.metadata?.name || pack.filename}</h4>
                <span className="pack-filename">{pack.filename}</span>
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
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderLoadedPacks = () => (
    <div className="content-pack-list">
      <h3>Currently Loaded Content Packs</h3>
      {loadedPacks.length === 0 ? (
        <p>No content packs are currently loaded.</p>
      ) : (
        <div className="pack-grid">
          {loadedPacks.map((pack, index) => (
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
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderExportForm = () => (
    <div className="export-form-container">
      <h3>Export Current State as Content Pack</h3>
      <form onSubmit={handleExport} className="export-form">
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
        </div>

        <button type="submit" disabled={exportLoading || !exportForm.filename}>
          {exportLoading ? 'Exporting...' : 'Export Content Pack'}
        </button>

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
          Available ({availablePacks.length})
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
        {activeTab === 'loaded' && renderLoadedPacks()}
        {activeTab === 'export' && renderExportForm()}
      </div>
    </div>
  );
};

export default ContentPackManager;