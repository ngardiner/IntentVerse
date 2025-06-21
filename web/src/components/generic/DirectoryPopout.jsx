import React, { useState } from 'react';
import { createDirectory } from '../../api/client';

const DirectoryPopout = ({ parentPath, onClose }) => {
  const [directoryName, setDirectoryName] = useState('');
  const [isValid, setIsValid] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState(null);

  const validateDirectoryName = (name) => {
    // Basic validation: non-empty and no invalid characters
    const isValid = name.trim() !== '' && !/[\\/:*?"<>|]/.test(name);
    setIsValid(isValid);
    return isValid;
  };

  const handleNameChange = (e) => {
    const name = e.target.value;
    setDirectoryName(name);
    validateDirectoryName(name);
  };

  const handleCreate = async () => {
    if (!isValid) {
      setError("Please enter a valid directory name");
      return;
    }
    
    const fullPath = `${parentPath}/${directoryName}`;
    
    try {
      setStatus('creating');
      const response = await createDirectory(fullPath);
      if (response.data.status === 'success') {
        setStatus('success');
        setTimeout(() => {
          onClose();
        }, 1500);
      } else {
        throw new Error('Directory creation failed');
      }
    } catch (err) {
      setStatus('error');
      setError(`Failed to create directory: ${err.message}`);
      console.error(err);
    }
  };

  return (
    <div className="directory-popout-overlay" onClick={onClose}>
      <div className="directory-popout-content" onClick={(e) => e.stopPropagation()}>
        <div className="directory-popout-header">
          <h3>Create New Directory</h3>
          <button className="directory-popout-close" onClick={onClose}>×</button>
        </div>
        <div className="directory-popout-body">
          <div className="directory-path-container">
            <span className="directory-parent-path">{parentPath}/</span>
            <input
              type="text"
              className={`directory-name-input ${!isValid && directoryName ? 'invalid' : ''}`}
              value={directoryName}
              onChange={handleNameChange}
              placeholder="Enter directory name"
              autoFocus
            />
          </div>
          
          {error && <div className="directory-error">{error}</div>}
          
          {status === 'creating' && (
            <div className="status-message creating">Creating directory...</div>
          )}
          {status === 'success' && (
            <div className="status-message success">Directory created successfully!</div>
          )}
          {status === 'error' && (
            <div className="status-message error">Failed to create directory.</div>
          )}
        </div>
        <div className="directory-popout-footer">
          <button 
            className="directory-popout-cancel" 
            onClick={onClose}
            disabled={status === 'creating'}
          >
            Cancel
          </button>
          <button 
            className="directory-popout-create" 
            onClick={handleCreate}
            disabled={!isValid || status === 'creating' || status === 'success'}
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
};

export default DirectoryPopout;