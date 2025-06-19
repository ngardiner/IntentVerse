import React, { useState, useEffect } from 'react';
import { getModuleState } from '../../api/client';

const GenericKeyValue = ({ title, data_source_api, sizeClass = '' }) => {
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
        if (Object.keys(data).length === 0) setLoading(true);

        const response = await getModuleState(moduleName);
        // We expect the data to be a simple key-value object
        setData(response.data || {});
        setError(null);
      } catch (err) {
        setError(`Failed to fetch state for ${moduleName}.`);
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchState(); // Initial fetch
    
    const intervalId = setInterval(fetchState, 3000);

    return () => clearInterval(intervalId);

  }, [data_source_api, data]);

  const renderContent = () => {
    if (loading) {
      return <p>Loading data...</p>;
    }
    if (error) {
      return <p className="error-message">{error}</p>;
    }
    const entries = Object.entries(data);
    if (entries.length === 0) {
      return <p>No items to display.</p>;
    }
    return (
      <dl className="key-value-list">
        {entries.map(([key, value]) => (
          <div key={key} className="kv-pair">
            <dt>{key}</dt>
            <dd>{String(value)}</dd>
          </div>
        ))}
      </dl>
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

export default GenericKeyValue;