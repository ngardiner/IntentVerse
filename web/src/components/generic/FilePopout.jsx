import React, { useState, useEffect } from 'react';
import { readFile, writeFile } from '../../api/client';

const FilePopout = ({ filePath, onClose }) => {
  const [content, setContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);

  useEffect(() => {
    const fetchFileContent = async () => {
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
  }, [filePath]);

  const handleSave = async () => {
    if (!filePath) return;
    
    try {
      setSaveStatus('saving');
      const response = await writeFile(filePath, editedContent);
      if (response.data.status === 'success') {
        setContent(editedContent);
        setSaveStatus('success');
        setTimeout(() => setSaveStatus(null), 2000);
        setIsEditing(false);
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
    setEditedContent(content);
    setIsEditing(false);
    setError(null);
  };

  if (!filePath) return null;

  // Extract filename from path
  const fileName = filePath.split('/').pop();

  return (
    <div className="file-popout-overlay" onClick={onClose}>
      <div className="file-popout-content" onClick={(e) => e.stopPropagation()}>
        <div className="file-popout-header">
          <h3>{fileName}</h3>
          <div className="file-popout-actions">
            {!isEditing && (
              <button 
                className="file-popout-edit" 
                onClick={() => setIsEditing(true)}
              >
                Edit
              </button>
            )}
            {isEditing && (
              <>
                <button 
                  className="file-popout-save" 
                  onClick={handleSave}
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
          ) : isEditing ? (
            <div className="file-editor">
              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                className="file-editor-textarea"
              />
            </div>
          ) : (
            <div className="file-viewer">
              <pre className="file-content">{content}</pre>
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