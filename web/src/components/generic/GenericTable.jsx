import React, { useState, useEffect } from 'react';
import { getModuleState } from '../../api/client';
import EmailPopout from './EmailPopout';

const GenericTable = ({ title, data_source_api, columns, sizeClass = '', module_id = '' }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const isEmailModule = module_id === 'email';

  useEffect(() => {
    const moduleName = data_source_api?.split('/')[3];

    const fetchState = async () => {
      if (!moduleName) {
        setError("Invalid API path provided for module state.");
        setLoading(false);
        return;
      }
      try {
        if (!data.length) setLoading(true); // Only show initial load spinner

        const response = await getModuleState(moduleName);
        // The API returns the state object, which might contain the array
        // We look for the first array property in the returned object.
        // This makes it flexible for different module state shapes.
        const dataArray = Object.values(response.data).find(Array.isArray) || [];
        setData(dataArray);
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

  }, [data_source_api, data.length]);

  const renderContent = () => {
    if (loading) {
      return <p>Loading data...</p>;
    }
    if (error) {
      return <p className="error-message">{error}</p>;
    }
    if (data.length === 0) {
      return <p>No items to display.</p>;
    }
    return (
      <table className="generic-table">
        <thead>
          <tr>
            {columns.map(col => <th key={col.header}>{col.header}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
            <tr 
              key={row.id || index}
              className={isEmailModule ? 'email-row' : ''}
              onClick={isEmailModule ? () => setSelectedEmail(row) : undefined}
            >
              {columns.map(col => (
                <td key={col.data_key}>{Array.isArray(row[col.data_key]) ? row[col.data_key].join(', ') : row[col.data_key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  return (
    <div className={`module-container ${sizeClass}`}>
      <h2>{title}</h2>
      <div className="module-content">
        {renderContent()}
      </div>
      {selectedEmail && (
        <EmailPopout email={selectedEmail} onClose={() => setSelectedEmail(null)} />
      )}
    </div>
  );
};

export default GenericTable;