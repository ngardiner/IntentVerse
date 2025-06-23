import React, { useState, useEffect } from 'react';
import { getModuleState } from '../../api/client';

const GenericKeyValue = ({ 
  title, 
  data_source_api, 
  sizeClass = '', 
  data_path = '',
  display_as = 'key_value',
  language = 'text',
  module_id = ''
}) => {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const moduleName = data_source_api?.split('/')[3];

    const fetchState = async () => {
      if (!moduleName) {
        setError("Invalid API path provided for module state.");
        setLoading(false);
        return;
      }
      try {
        // Only show loading spinner on initial load, not during refreshes
        if (Object.keys(data).length === 0 && loading) {
          // Keep the loading state to avoid flickering
        } else if (Object.keys(data).length === 0) {
          setLoading(true);
        }

        const response = await getModuleState(moduleName);
        
        // Extract data using data_path if provided
        let extractedData = response.data;
        if (data_path) {
          const pathParts = data_path.split('.');
          for (const part of pathParts) {
            if (extractedData && extractedData[part] !== undefined) {
              extractedData = extractedData[part];
            } else {
              extractedData = {};
              break;
            }
          }
        }
        
        setData(extractedData || {});
        setError(null);
      } catch (err) {
        setError(`Failed to fetch state for ${moduleName}.`);
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    // Create a debounced version of fetchState to reduce flickering
    const debouncedFetchState = () => {
      // Use setTimeout to debounce the fetch
      const timeoutId = setTimeout(() => {
        fetchState();
      }, 100); // Small delay to batch potential multiple updates
      
      // Return a cleanup function that cancels the timeout if component unmounts
      return () => clearTimeout(timeoutId);
    };

    fetchState(); // Initial fetch
    
    // Use a longer interval to reduce flickering (5 seconds instead of 3)
    const intervalId = setInterval(debouncedFetchState, 5000);

    return () => clearInterval(intervalId);

  }, [data_source_api, data_path]);

  const formatValue = (value) => {
    if (value === null || value === undefined) {
      return <span className="null-value">NULL</span>;
    }
    
    if (typeof value === 'object') {
      if (Array.isArray(value)) {
        return <span className="array-value">[{value.map(String).join(', ')}]</span>;
      }
      return <pre className="object-value">{JSON.stringify(value, null, 2)}</pre>;
    }
    
    return String(value);
  };

  const renderCodeBlock = () => {
    const content = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    return (
      <pre className={`code-block ${language}`}>
        <code>{content}</code>
      </pre>
    );
  };

  const renderKeyValueList = () => {
    const entries = Object.entries(data);
    if (entries.length === 0) {
      return <p>No items to display.</p>;
    }
    
    // Use a stable key for the list to prevent unnecessary re-renders
    const listKey = `kv-list-${module_id}`;
    
    return (
      <dl className="key-value-list" key={listKey}>
        {entries.map(([key, value]) => (
          <div key={key} className="kv-pair">
            <dt>{key}</dt>
            <dd>{formatValue(value)}</dd>
          </div>
        ))}
      </dl>
    );
  };

  const renderContent = () => {
    if (loading) {
      return <p>Loading data...</p>;
    }
    if (error) {
      return <p className="error-message">{error}</p>;
    }
    
    if (display_as === 'code_block') {
      return renderCodeBlock();
    }
    
    return renderKeyValueList();
  };


  return (
    <div 
      className={`module-container`} 
      data-module-id={module_id}
    >
      <h2>{title}</h2>
      <div className="module-content">
        {renderContent()}
      </div>
    </div>
  );
};

export default GenericKeyValue;