import React, { useState, useEffect } from 'react';
import { getModuleState, deleteFile } from '../../api/client';
import FilePopout from './FilePopout';
import ConfirmationPopup from './ConfirmationPopup';

// A small, recursive helper component to render each node in the tree.
const TreeNode = ({ node, path = '/', onFileClick, onCreateFile, onDeleteFile }) => {
  if (!node) {
    return null;
  }

  const isDirectory = node.type === 'directory';
  const icon = isDirectory ? '📁' : '📄';
  const currentPath = path === '/' ? `/${node.name}` : `${path}/${node.name}`;
  const [isHovering, setIsHovering] = useState(false);

  const handleClick = () => {
    if (!isDirectory && onFileClick) {
      onFileClick(currentPath);
    }
  };

  const handleCreateFile = (e) => {
    e.stopPropagation();
    if (onCreateFile) {
      onCreateFile(currentPath);
    }
  };
  
  const handleDeleteFile = (e) => {
    e.stopPropagation();
    if (onDeleteFile) {
      onDeleteFile(currentPath);
    }
  };

  return (
    <li className="treenode">
      <div 
        className={`tree-node-container ${isDirectory ? 'directory-node' : 'file-node'}`}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
      >
        <span onClick={handleClick}>
          {icon} {node.name}
        </span>
        {isHovering && (
          <div className={isDirectory ? "directory-actions" : "file-actions"}>
            {isDirectory && (
              <button 
                className="create-file-btn" 
                title="Create new file"
                onClick={handleCreateFile}
              >
                +
              </button>
            )}
            {!isDirectory && (
              <button 
                className="delete-file-btn" 
                title="Delete file"
                onClick={handleDeleteFile}
              >
                ×
              </button>
            )}
          </div>
        )}
      </div>
      {/* If the node is a directory and has children, recursively render them */}
      {isDirectory && node.children && node.children.length > 0 && (
        <ul>
          {node.children.map((child, index) => (
            <TreeNode 
              key={child.name + index} 
              node={child} 
              path={currentPath}
              onFileClick={onFileClick}
              onCreateFile={onCreateFile}
              onDeleteFile={onDeleteFile}
            />
          ))}
        </ul>
      )}
    </li>
  );
};


const GenericFileTree = ({ title, data_source_api, sizeClass = '', module_id = '' }) => {
  const [treeData, setTreeData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFilePath, setSelectedFilePath] = useState(null);
  const [isCreatingFile, setIsCreatingFile] = useState(false);
  const [newFileDirectory, setNewFileDirectory] = useState(null);
  const [fileToDelete, setFileToDelete] = useState(null);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
  const [deleteStatus, setDeleteStatus] = useState(null);

  useEffect(() => {
    // A simple way to extract the module name (e.g., 'filesystem') from the API path
    const moduleName = data_source_api?.split('/')[3];

    const fetchState = async () => {
      if (!moduleName) {
        setError("Invalid API path provided for module state.");
        setLoading(false);
        return;
      }
      try {
        // Don't show loading spinner on background polls
        if (!treeData) setLoading(true);

        const response = await getModuleState(moduleName);
        setTreeData(response.data);
        setError(null);
      } catch (err) {
        setError(`Failed to fetch state for ${moduleName}. Is the core service running?`);
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchState(); // Initial fetch
    
    // Set up an interval to poll for updates every 3 seconds
    const intervalId = setInterval(fetchState, 3000);

    // This is a cleanup function that React runs when the component is unmounted.
    // It's crucial for preventing memory leaks.
    return () => clearInterval(intervalId);

  }, [data_source_api, treeData]); // Re-run effect if the api path changes

  const handleFileClick = (filePath) => {
    setSelectedFilePath(filePath);
    setIsCreatingFile(false);
  };

  const handleCreateFile = (directoryPath) => {
    setNewFileDirectory(directoryPath);
    setIsCreatingFile(true);
    setSelectedFilePath(null);
  };

  const handleDeleteFile = (filePath) => {
    setFileToDelete(filePath);
    setShowDeleteConfirmation(true);
  };

  const confirmDeleteFile = async () => {
    try {
      setDeleteStatus('deleting');
      const response = await deleteFile(fileToDelete);
      if (response.data.status === 'success') {
        setDeleteStatus('success');
        // Close the confirmation after a short delay
        setTimeout(() => {
          setShowDeleteConfirmation(false);
          setFileToDelete(null);
          setDeleteStatus(null);
        }, 1500);
      } else {
        throw new Error('Delete operation failed');
      }
    } catch (err) {
      setDeleteStatus('error');
      console.error('Error deleting file:', err);
      // Keep the popup open to show the error
    }
  };

  const cancelDeleteFile = () => {
    setShowDeleteConfirmation(false);
    setFileToDelete(null);
    setDeleteStatus(null);
  };

  const handleClosePopout = () => {
    setSelectedFilePath(null);
    setIsCreatingFile(false);
    setNewFileDirectory(null);
  };

  const renderContent = () => {
    if (loading) {
      return <p>Loading file system...</p>;
    }
    if (error) {
      return <p className="error-message">{error}</p>;
    }
    if (!treeData) {
      return <p>No file system data available.</p>;
    }
    return (
      <ul className="file-tree-root">
        <TreeNode 
          node={treeData} 
          onFileClick={handleFileClick}
          onCreateFile={handleCreateFile}
          onDeleteFile={handleDeleteFile}
        />
      </ul>
    );
  };

  return (
    <div className={`module-container`} data-module-id={module_id}>
      <h2>{title}</h2>
      <div className="module-content">
        {renderContent()}
      </div>
      {selectedFilePath && (
        <FilePopout 
          filePath={selectedFilePath} 
          onClose={handleClosePopout} 
          isNewFile={false}
        />
      )}
      {isCreatingFile && (
        <FilePopout 
          filePath={newFileDirectory} 
          onClose={handleClosePopout} 
          isNewFile={true}
        />
      )}
      {showDeleteConfirmation && (
        <ConfirmationPopup
          message={
            deleteStatus === 'deleting' ? 
              "Deleting file..." : 
            deleteStatus === 'success' ? 
              "File deleted successfully!" : 
            deleteStatus === 'error' ? 
              "Error deleting file. Please try again." : 
              `Are you sure you want to delete "${fileToDelete.split('/').pop()}"?`
          }
          onConfirm={confirmDeleteFile}
          onCancel={cancelDeleteFile}
          status={deleteStatus}
        />
      )}
    </div>
  );
};

export default GenericFileTree;