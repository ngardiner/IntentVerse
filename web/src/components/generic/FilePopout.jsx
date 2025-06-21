import React, { useState, useEffect } from 'react';
import { readFile, writeFile } from '../../api/client';

const FilePopout = ({ filePath, onClose, isNewFile = false }) => {
  const [content, setContent] = useState('');
  const [isEditing, setIsEditing] = useState(isNewFile);
  const [editedContent, setEditedContent] = useState('');
  const [loading, setLoading] = useState(!isNewFile);
  const [error, setError] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);
  
  // For file name editing
  const initialFileName = isNewFile ? '' : filePath.split('/').pop();
  const directoryPath = isNewFile ? filePath : filePath.substring(0, filePath.lastIndexOf('/'));
  const [fileName, setFileName] = useState(initialFileName);
  const [isFileNameValid, setIsFileNameValid] = useState(!isNewFile);
  const [isEditingFileName, setIsEditingFileName] = useState(isNewFile);

  useEffect(() => {
    const fetchFileContent = async () => {
      if (isNewFile) {
        setContent('');
        setEditedContent('');
        setLoading(false);
        return;
      }
      
      if (!filePath) return;
      
      try {
        setLoading(true);
        const response = await readFile(filePath);
        // The execute endpoint returns { status: "success", result: <actual result> }
        const fileContent = response.data.result;
        setContent(fileContent);
        setEditedContent(fileContent);
        setError(null);
      } catch (err) {
        setError(`Failed to fetch file content: ${err.message}`);
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchFileContent();
  }, [filePath, isNewFile]);

  useEffect(() => {
    validateFileName(fileName);
  }, [fileName]);

  const validateFileName = (name) => {
    // Basic validation: non-empty and no invalid characters
    const isValid = name.trim() !== '' && !/[\\/:*?"<>|]/.test(name);
    setIsFileNameValid(isValid);
    return isValid;
  };

  const handleSave = async () => {
    if (!isFileNameValid) {
      setError("Please enter a valid file name");
      return;
    }
    
    const fullPath = `${directoryPath}/${fileName}`;
    
    try {
      setSaveStatus('saving');
      const response = await writeFile(fullPath, editedContent);
      if (response.data.status === 'success') {
        setContent(editedContent);
        setSaveStatus('success');
        setTimeout(() => setSaveStatus(null), 2000);
        setIsEditing(false);
        setIsEditingFileName(false);
        
        // If this was a new file or a renamed file, we might want to refresh the file tree
        // This will happen automatically due to the polling in GenericFileTree
      } else {
        throw new Error('Save operation failed');
      }
    } catch (err) {
      setSaveStatus('error');
      setError(`Failed to save file: ${err.message}`);
      console.error(err);
    }
  };

  const handleCancel = () => {
    if (isNewFile) {
      onClose();
      return;
    }
    
    setEditedContent(content);
    setFileName(initialFileName);
    setIsEditing(false);
    setIsEditingFileName(false);
    setError(null);
  };

  const handleFileNameClick = () => {
    if (!isNewFile && !isEditing) {
      setIsEditingFileName(true);
    }
  };

  if (!filePath && !isNewFile) return null;

  return (
    <div className="file-popout-overlay" onClick={onClose}>
      <div className="file-popout-content" onClick={(e) => e.stopPropagation()}>
        <div className="file-popout-header">
          <div className="file-path-container">
            <span className="file-directory-path">{directoryPath}/</span>
            {isEditingFileName ? (
              <input
                type="text"
                className={`file-name-input ${!isFileNameValid ? 'invalid' : ''}`}
                value={fileName}
                onChange={(e) => setFileName(e.target.value)}
                placeholder="Enter file name"
                autoFocus
              />
            ) : (
              <span 
                className="file-name" 
                onClick={handleFileNameClick}
                title={isNewFile || isEditing ? "" : "Click to rename"}
              >
                {fileName || "(New File)"}
              </span>
            )}
          </div>
          <div className="file-popout-actions">
            {!isEditing && !isNewFile && (
              <button 
                className="file-popout-edit" 
                onClick={() => setIsEditing(true)}
              >
                Edit
              </button>
            )}
            {(isEditing || isNewFile) && (
              <>
                <button 
                  className="file-popout-save" 
                  onClick={handleSave}
                  disabled={!isFileNameValid}
                >
                  Save
                </button>
                <button 
                  className="file-popout-cancel" 
                  onClick={handleCancel}
                >
                  Cancel
                </button>
              </>
            )}
            <button className="file-popout-close" onClick={onClose}>×</button>
          </div>
        </div>
        <div className="file-popout-body">
          {loading ? (
            <div className="file-loading">Loading file content...</div>
          ) : error ? (
            <div className="file-error">{error}</div>
          ) : isEditing || isNewFile ? (
            <div className="file-editor">
              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                className="file-editor-textarea"
                placeholder="Enter file content here..."
              />
            </div>
          ) : (
            <div className="file-viewer">
              <pre className="file-content">{content}</pre>
            </div>
          )}
          {!isFileNameValid && isEditingFileName && (
            <div className="validation-error">
              Please enter a valid file name (no empty names or special characters like \/:*?"&lt;&gt;|)
            </div>
          )}
          {saveStatus === 'saving' && (
            <div className="save-status saving">Saving...</div>
          )}
          {saveStatus === 'success' && (
            <div className="save-status success">File saved successfully!</div>
          )}
          {saveStatus === 'error' && (
            <div className="save-status error">Failed to save file. Please try again.</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FilePopout;