import React, { useState, useEffect } from 'react';
import { getModuleState } from '../../api/client';
import EmailPopout from './EmailPopout';

const GenericTable = ({ 
  title, 
  data_source_api, 
  columns, 
  sizeClass = '', 
  module_id = '', 
  data_path = '',
  dynamic_columns = false,
  max_rows = 1000,
  moduleState = null,
  data_transform = null
}) => {
  const [data, setData] = useState([]);
  const [dynamicHeaders, setDynamicHeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const [lastRetryTime, setLastRetryTime] = useState(0);
  const isEmailModule = module_id === 'email';
  const isDatabaseModule = module_id === 'database';

  const processModuleState = (stateData) => {
      // Extract data using data_path if provided
      let extractedData = stateData;
      if (data_path) {
        const pathParts = data_path.split('.');
        for (const part of pathParts) {
          if (extractedData && extractedData[part] !== undefined) {
            extractedData = extractedData[part];
          } else {
            extractedData = [];
            break;
          }
        }
      }
      
      // Handle different data formats
      let dataArray = [];
      let newDynamicHeaders = [];
      
      if (Array.isArray(extractedData)) {
        dataArray = extractedData.slice(0, max_rows); // Apply max_rows limit to all arrays
        
        // Generate dynamic headers for array data when dynamic_columns is true
        if (dynamic_columns && dataArray.length > 0) {
          if (typeof dataArray[0] === 'object' && dataArray[0] !== null) {
            newDynamicHeaders = Object.keys(dataArray[0]);
          } else if (Array.isArray(dataArray[0])) {
            newDynamicHeaders = dataArray[0].map((_, index) => `Column ${index + 1}`);
          } else {
            newDynamicHeaders = ['Value'];
          }
        }
        
        // Special handling for email module to ensure data is properly formatted
        if (isEmailModule && dataArray.length > 0) {
          // Process email data to ensure all required fields are present
          dataArray = dataArray.map(email => ({
            ...email,
            // Ensure 'to' is always an array
            to: Array.isArray(email.to) ? email.to : (email.to ? [email.to] : []),
            // Ensure 'from' exists
            from: email.from || "unknown@example.com",
            // Ensure timestamp exists
            timestamp: email.timestamp || new Date().toISOString(),
            // Ensure subject exists
            subject: email.subject || "(No Subject)",
            // Ensure body exists
            body: email.body || ""
          }));
          
          // Regenerate dynamic headers after email processing if needed
          if (dynamic_columns && dataArray.length > 0 && typeof dataArray[0] === 'object' && dataArray[0] !== null) {
            newDynamicHeaders = Object.keys(dataArray[0]);
          }
        }
      } else if (typeof extractedData === 'object' && extractedData !== null) {
        // Convert object to array if it's not already an array
        if (Object.keys(extractedData).length > 0) {
          // Handle data_transform property
          if (data_transform === 'object_to_array') {
            dataArray = Object.entries(extractedData).map(([name, details]) => ({
              name,
              ...details
            }));
          } else if (isDatabaseModule && data_path === 'tables') {
            // Legacy fallback for database tables
            dataArray = Object.entries(extractedData).map(([name, details]) => ({
              name,
              ...details
            }));
          } else if (isDatabaseModule && data_path === 'last_query_result') {
            // Handle database query results - SIMPLIFIED
            console.log('Processing last_query_result:', extractedData);
            
            if (extractedData && typeof extractedData === 'object') {
              // Get rows and columns
              const rows = extractedData.rows || [];
              const columns = extractedData.columns || [];
              
              console.log('Extracted rows:', rows.length, 'columns:', columns.length);
              
              dataArray = rows.slice(0, max_rows);
              
              if (dynamic_columns) {
                if (columns.length > 0) {
                  // Use provided columns
                  newDynamicHeaders = columns;
                  console.log('Using provided columns:', newDynamicHeaders);
                } else if (dataArray.length > 0) {
                  // Generate fallback columns
                  if (Array.isArray(dataArray[0])) {
                    newDynamicHeaders = dataArray[0].map((_, index) => `Column ${index + 1}`);
                  } else if (typeof dataArray[0] === 'object' && dataArray[0] !== null) {
                    newDynamicHeaders = Object.keys(dataArray[0]);
                  } else {
                    newDynamicHeaders = ['Value'];
                  }
                  console.log('Generated fallback columns:', newDynamicHeaders);
                } else {
                  newDynamicHeaders = [];
                  console.log('No data, empty columns');
                }
              }
            } else {
              console.log('Invalid extractedData for last_query_result');
              dataArray = [];
              newDynamicHeaders = [];
            }
          } else {
            // Generic object to array conversion
            dataArray = Object.entries(extractedData).map(([key, value]) => ({
              key,
              value: typeof value === 'object' ? JSON.stringify(value) : value
            }));
          }
        }
      }
      
      // Update state with both data and headers atomically to prevent race conditions
      console.log('Setting data:', dataArray.length, 'rows, headers:', newDynamicHeaders.length);
      setData(dataArray);
      if (dynamic_columns) {
        setDynamicHeaders(newDynamicHeaders);
      }
      setError(null);
      setLoading(false);
      setRetryCount(0); // Reset retry count on successful data processing
    };

  // Function to handle manual refresh
  const handleManualRefresh = async () => {
    const moduleName = data_source_api?.split('/')[3];
    if (!moduleName) return;
    
    setLoading(true);
    setError(null);
    setRetryCount(prev => prev + 1);
    setLastRetryTime(Date.now());
    
    try {
      const response = await getModuleState(moduleName);
      processModuleState(response.data);
    } catch (err) {
      setError(`Failed to refresh data for ${moduleName}.`);
      console.error(err);
      setLoading(false);
    }
  };

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
        if (!data.length && loading) {
          // Keep the loading state to avoid flickering
        } else if (!data.length) {
          setLoading(true);
        }

        // Fetch data from the API
        const response = await getModuleState(moduleName);
        processModuleState(response.data);
      } catch (err) {
        setError(`Failed to fetch state for ${moduleName}.`);
        console.error(err);
        setLoading(false);
      }
    };

    // If moduleState is provided (from parent SwitchableView), use it directly
    if (moduleState !== null) {
      processModuleState(moduleState);
      return; // Don't set up polling when using provided state
    }

    // Otherwise, fetch state independently (for standalone usage)
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

  }, [data_source_api, data_path, dynamic_columns, isEmailModule, moduleState]);

  // Auto-retry mechanism for stuck "Loading column configuration..." state
  useEffect(() => {
    if (!dynamic_columns || !isDatabaseModule) return;
    
    // Check if we're stuck in the loading column configuration state
    const isStuckInLoadingColumns = !loading && data.length > 0 && dynamicHeaders.length === 0;
    
    if (isStuckInLoadingColumns && retryCount < 3) {
      const timeSinceLastRetry = Date.now() - lastRetryTime;
      const shouldRetry = timeSinceLastRetry > 2000; // Wait at least 2 seconds between retries
      
      if (shouldRetry) {
        console.log(`Auto-retrying stuck column configuration (attempt ${retryCount + 1}/3)`, {
          data: data.length,
          dynamicHeaders: dynamicHeaders.length,
          loading,
          retryCount
        });
        handleManualRefresh();
      }
    }
  }, [data, dynamicHeaders, loading, retryCount, lastRetryTime, dynamic_columns, isDatabaseModule]);

  // Timeout mechanism to prevent infinite loading states
  useEffect(() => {
    if (!dynamic_columns || !isDatabaseModule || loading) return;
    
    const isStuckInLoadingColumns = data.length > 0 && dynamicHeaders.length === 0;
    
    if (isStuckInLoadingColumns && retryCount >= 3) {
      // After 3 retries, set an error state with manual refresh option
      const timeoutId = setTimeout(() => {
        if (data.length > 0 && dynamicHeaders.length === 0) {
          console.warn('Column configuration timeout reached, setting error state');
          setError('Unable to load column configuration. Data may be malformed.');
        }
      }, 10000); // 10 second timeout
      
      return () => clearTimeout(timeoutId);
    }
  }, [data, dynamicHeaders, loading, retryCount, dynamic_columns, isDatabaseModule]);

  const formatCellValue = (value, columnKey) => {
    if (value === null || value === undefined) {
      return <span className="null-value">NULL</span>;
    }
    
    // Special handling for email module
    if (isEmailModule) {
      if (columnKey === 'timestamp') {
        // Format the timestamp as a readable date
        try {
          const date = new Date(value);
          if (!isNaN(date.getTime())) {
            return date.toLocaleString();
          }
        } catch (e) {
          console.warn("Error formatting date:", e);
        }
        return value || "Unknown Date";
      }
      
      if (columnKey === 'to') {
        if (Array.isArray(value)) {
          return value.length > 0 ? value.join(', ') : "No Recipients";
        } else if (typeof value === 'string') {
          return value || "No Recipients";
        }
        return "No Recipients";
      }
      
      if (columnKey === 'subject') {
        return value || "(No Subject)";
      }
    }
    
    // General handling for other types
    if (Array.isArray(value)) {
      return value.length > 0 ? value.join(', ') : "";
    }
    
    if (typeof value === 'object' && value !== null) {
      try {
        return <span className="object-value">{JSON.stringify(value)}</span>;
      } catch (e) {
        return <span className="object-value">[Complex Object]</span>;
      }
    }
    
    return value;
  };

  const renderContent = () => {
    if (loading) {
      return <p>Loading data...</p>;
    }
    if (error) {
      return (
        <div className="error-state">
          <p className="error-message">{error}</p>
          <button 
            className="btn btn-secondary btn-small" 
            onClick={handleManualRefresh}
            disabled={loading}
            style={{ marginTop: '0.5rem' }}
          >
            {loading ? 'Refreshing...' : 'Try Again'}
          </button>
        </div>
      );
    }
    if (data.length === 0) {
      // Show table headers even when empty, but with a "no data" message in the tbody
      const hasColumnsToRender = (columns && columns.length > 0) || (dynamic_columns && dynamicHeaders.length > 0);
      
      if (!hasColumnsToRender) {
        return <p>No items to display.</p>;
      }
      
      const usesDynamicColumns = dynamic_columns && dynamicHeaders.length > 0;
      
      return (
        <div className="table-container">
          <table className={`generic-table ${isDatabaseModule ? 'database-table' : ''}`}>
            <thead>
              <tr>
                {usesDynamicColumns ? 
                  dynamicHeaders.map((header, index) => <th key={index}>{header}</th>) :
                  columns.map(col => <th key={col.header}>{col.header}</th>)
                }
              </tr>
            </thead>
            <tbody>
              <tr>
                <td 
                  colSpan={usesDynamicColumns ? dynamicHeaders.length : columns.length}
                  style={{ textAlign: 'center', fontStyle: 'italic', color: '#666' }}
                >
                  No items to display.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      );
    }
    
    // Determine if we should use dynamic columns or predefined columns
    const usesDynamicColumns = dynamic_columns && dynamicHeaders.length > 0;
    
    // Check if we have columns to render - either dynamic headers or predefined columns
    const hasColumnsToRender = usesDynamicColumns || (columns && columns.length > 0);
    
    // For dynamic columns, if we have data but no headers, just show the data anyway
    if (dynamic_columns && data.length > 0 && dynamicHeaders.length === 0) {
      console.log('STUCK STATE DETECTED - showing data anyway');
      // Just show the data with generic column names
      const fallbackHeaders = data[0] ? 
        (Array.isArray(data[0]) ? 
          data[0].map((_, i) => `Column ${i + 1}`) : 
          Object.keys(data[0])
        ) : ['Data'];
      
      return (
        <div className="table-container">
          <table className={`generic-table ${isDatabaseModule ? 'database-table' : ''}`}>
            <thead>
              <tr>
                {fallbackHeaders.map((header, index) => <th key={index}>{header}</th>)}
              </tr>
            </thead>
            <tbody>
              {data.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {fallbackHeaders.map((header, colIndex) => {
                    let cellValue;
                    if (Array.isArray(row)) {
                      cellValue = row[colIndex];
                    } else if (typeof row === 'object' && row !== null) {
                      cellValue = row[header];
                    } else {
                      cellValue = row;
                    }
                    return <td key={colIndex}>{formatCellValue(cellValue, header)}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    
    if (!hasColumnsToRender) {
      return <p>No column configuration available to display data.</p>;
    }
    
    // Use a stable key for the table to prevent unnecessary re-renders
    const tableKey = `table-${module_id}`;
    
    return (
      <div className="table-container">
        <table 
          className={`generic-table ${isDatabaseModule ? 'database-table' : ''}`}
          key={tableKey}
        >
          <thead>
            <tr>
              {usesDynamicColumns ? 
                dynamicHeaders.map((header, index) => <th key={index}>{header}</th>) :
                columns.map(col => <th key={col.header}>{col.header}</th>)
              }
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIndex) => (
              <tr 
                key={row.id || row.email_id || rowIndex}
                className={isEmailModule ? 'email-row' : ''}
                onClick={isEmailModule ? () => setSelectedEmail(row) : undefined}
              >
                {usesDynamicColumns ? 
                  // For dynamic columns, handle both array and object rows
                  dynamicHeaders.map((header, colIndex) => {
                    let cellValue;
                    if (Array.isArray(row)) {
                      // Row is an array, use column index
                      cellValue = row[colIndex];
                    } else if (typeof row === 'object' && row !== null) {
                      // Row is an object, use header as key
                      cellValue = row[header];
                    } else {
                      cellValue = row;
                    }
                    return <td key={colIndex}>{formatCellValue(cellValue, header)}</td>;
                  }) :
                  // For predefined columns, use the data_key from columns
                  columns.map(col => (
                    <td key={col.data_key}>{formatCellValue(row[col.data_key], col.data_key)}</td>
                  ))
                }
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
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
      {selectedEmail && (
        <EmailPopout email={selectedEmail} onClose={() => setSelectedEmail(null)} />
      )}
    </div>
  );
};

export default GenericTable;