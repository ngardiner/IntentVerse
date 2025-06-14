import React, { useState, useEffect } from 'react';
import { getModuleState } from '../../api/client';

// A small, recursive component to render each node in the tree.
const TreeNode = ({ node }) => {
  if (!node) {
    return null;
  }

  const isDirectory = node.type === 'directory';
  const icon = isDirectory ? '📁' : '📄';

  return (
    <li>
      <span>{icon} {node.name}</span>
      {isDirectory && node.children && node.children.length > 0 && (
        <ul>
          {node.children.map(child => (
            <TreeNode key={child.name} node={child} />
          ))}
        </ul>
      )}
    </li>
  );
};


const GenericFileTree = ({ title, data_source_api }) => {
  const [treeData, setTreeData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // A simple way to extract the module name from the API path
    const moduleName = data_source_api.split('/')[3];

    const fetchState = async () => {
      if (!moduleName) {
        setError("Invalid API path provided for module state.");
        setLoading(false);
        return;
      }
      try {
        setLoading(true);
        const response = await getModuleState(moduleName);
        setTreeData(response.data);
        setError(null);
      } catch (err) {
        setError(`Failed to fetch state for ${moduleName}.`);
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchState();
    
    // Set up an interval to poll for updates every 5 seconds
    const intervalId = setInterval(fetchState, 5000);

    // Cleanup the interval when the component unmounts
    return () => clearInterval(intervalId);

  }, [data_source_api]); // Re-run effect if the api path changes

  const renderContent = () => {
    if (loading && !treeData) {
      return <p>Loading file system...</p>;
    }
    if (error) {
      return <p className="error-message">{error}</p>;
    }
    if (!treeData) {
      return <p>No file system data available.</p>;
    }
    return (
      <ul>
        <TreeNode node={treeData} />
      </ul>
    );
  };

  return (
    <div className="module-container">
      <h2>{title}</h2>
      <div className="module-content file-tree">
        {renderContent()}
      </div>
    </div>
  );
};

export default GenericFileTree;