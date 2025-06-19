import React, { useState, useEffect } from 'react';
import { getModuleState } from '../../api/client';

// A small, recursive helper component to render each node in the tree.
const TreeNode = ({ node }) => {
  if (!node) {
    return null;
  }

  const isDirectory = node.type === 'directory';
  const icon = isDirectory ? '📁' : '📄';

  return (
    <li className="treenode">
      <span>{icon} {node.name}</span>
      {/* If the node is a directory and has children, recursively render them */}
      {isDirectory && node.children && node.children.length > 0 && (
        <ul>
          {node.children.map((child, index) => (
            <TreeNode key={child.name + index} node={child} />
          ))}
        </ul>
      )}
    </li>
  );
};


const GenericFileTree = ({ title, data_source_api, sizeClass = '' }) => {
  const [treeData, setTreeData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
        <TreeNode node={treeData} />
      </ul>
    );
  };

  return (
    <div className={`module-container ${sizeClass}`}>
      <h2>{title}</h2>
      <div className="module-content">
        {renderContent()}
      </div>
    </div>
  );
};

export default GenericFileTree;