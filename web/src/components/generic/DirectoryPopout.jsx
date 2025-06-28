import React, { useState } from 'react';
import { createDirectory } from '../../api/client';

const DirectoryPopout = ({ parentPath, onClose }) => {
  const [directoryName, setDirectoryName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && directoryName.trim()) {
      handleCreate();
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  const handleCreate = async () => {
    if (!directoryName.trim()) return;
    
    const fullPath = parentPath === '/' ? `/${directoryName}` : `${parentPath}/${directoryName}`;
    
    try {
      setIsCreating(true);
      await createDirectory(fullPath);
      onClose(); // Close immediately on success
    } catch (err) {
      console.error('Failed to create directory:', err);
      // Could add error handling here if needed
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="popup-overlay" onClick={onClose}>
      <div className="popup-content compact-popup" onClick={(e) => e.stopPropagation()}>
        <div className="popup-header">
          <span>New Directory</span>
        </div>
        <div className="popup-body">
          <input
            type="text"
            value={directoryName}
            onChange={(e) => setDirectoryName(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Directory name"
            className="popup-input"
            autoFocus
            disabled={isCreating}
          />
        </div>
        <div className="popup-actions">
          <button 
            onClick={onClose}
            className="popup-btn popup-btn-cancel"
            disabled={isCreating}
          >
            Cancel
          </button>
          <button 
            onClick={handleCreate}
            className="popup-btn popup-btn-primary"
            disabled={!directoryName.trim() || isCreating}
          >
            {isCreating ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DirectoryPopout;