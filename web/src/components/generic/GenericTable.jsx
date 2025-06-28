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
  moduleState = null
}) => {
  const [data, setData] = useState([]);
  const [dynamicHeaders, setDynamicHeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const isEmailModule = module_id === 'email';
  const isDatabaseModule = module_id === 'database';

  useEffect(() => {
    const moduleName = data_source_api?.split('/')[3];

    const processModuleState = (stateData) => {
      console.log('GenericTable processModuleState called with:', {
        stateData,
        data_path,
        dynamic_columns,
        module_id
      });
      
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
        dataArray = extractedData;
        
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
        }
      } else if (typeof extractedData === 'object' && extractedData !== null) {
        // Convert object to array if it's not already an array
        if (Object.keys(extractedData).length > 0) {
          // For database tables or similar structures
          if (isDatabaseModule && data_path === 'tables') {
            dataArray = Object.entries(extractedData).map(([name, details]) => ({
              name,
              ...details
            }));
          } else if (isDatabaseModule && data_path === 'last_query_result') {
            // Handle database query results
            console.log('Processing database query results:', {
              extractedData,
              hasRows: Array.isArray(extractedData?.rows),
              rowsLength: extractedData?.rows?.length,
              hasColumns: Array.isArray(extractedData?.columns),
              columnsLength: extractedData?.columns?.length,
              columns: extractedData?.columns
            });
            
            if (extractedData && typeof extractedData === 'object') {
              // Check if we have rows data
              if (Array.isArray(extractedData.rows)) {
                dataArray = extractedData.rows.slice(0, max_rows);
                
                // Set dynamic headers if available
                if (dynamic_columns && extractedData.columns && Array.isArray(extractedData.columns) && extractedData.columns.length > 0) {
                  newDynamicHeaders = extractedData.columns;
                  console.log('Set dynamic headers from columns:', newDynamicHeaders);
                } else if (dynamic_columns) {
                  // If no columns are provided but we have data, try to infer columns from the first row
                  if (dataArray.length > 0 && Array.isArray(dataArray[0])) {
                    // Generate column headers like "Column 1", "Column 2", etc.
                    newDynamicHeaders = dataArray[0].map((_, index) => `Column ${index + 1}`);
                  } else {
                    // No data to infer columns from
                    newDynamicHeaders = [];
                  }
                }
              } else {
                // No rows data available
                dataArray = [];
                if (dynamic_columns) {
                  newDynamicHeaders = [];
                }
              }
            } else {
              // extractedData is not a valid object
              dataArray = [];
              if (dynamic_columns) {
                newDynamicHeaders = [];
              }
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
      console.log('Setting state:', {
        dataArray,
        newDynamicHeaders,
        dynamic_columns
      });
      
      setData(dataArray);
      if (dynamic_columns) {
        setDynamicHeaders(newDynamicHeaders);
      }
      setError(null);
      setLoading(false);
    };

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
      console.log('Using provided moduleState:', moduleState);
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
      return <p className="error-message">{error}</p>;
    }
    if (data.length === 0) {
      return <p>No items to display.</p>;
    }
    
    // Determine if we should use dynamic columns or predefined columns
    const usesDynamicColumns = dynamic_columns && dynamicHeaders.length > 0;
    
    // Check if we have columns to render - either dynamic headers or predefined columns
    const hasColumnsToRender = usesDynamicColumns || (columns && columns.length > 0);
    
    // For dynamic columns, if we have data but no headers yet, show loading
    // This handles the case where data is fetched but headers are still being processed
    if (dynamic_columns && data.length > 0 && dynamicHeaders.length === 0) {
      return <p>Loading column configuration...</p>;
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
                  // For dynamic columns, use the headers as keys
                  dynamicHeaders.map((header, colIndex) => (
                    <td key={colIndex}>{formatCellValue(row[colIndex], header)}</td>
                  )) :
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