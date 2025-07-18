import React, { useState, useEffect } from 'react';
import { getModuleState } from '../../api/client';
import GenericTable from './GenericTable';
import GenericKeyValue from './GenericKeyValue';
import GenericFileTree from './GenericFileTree';
import EmailPopout from './EmailPopout';
import QueryExecutor from './QueryExecutor';
import CreateEmailButton from './CreateEmailButton';

const SwitchableView = ({ 
  title,
  description,
  module_id,
  data_source_api,
  views,
  sizeClass = '',
}) => {
  // Use the first view in the array as the default view
  const [activeViewIndex, setActiveViewIndex] = useState(0);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [moduleState, setModuleState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [showPopout, setShowPopout] = useState(false);

  useEffect(() => {
    // Extract the module name from the API path
    const moduleName = data_source_api?.split('/')[3];

    const fetchState = async () => {
      if (!moduleName) {
        setError("Invalid API path provided for module state.");
        setLoading(false);
        return;
      }
      try {
        // Only show loading spinner on initial load, not during refreshes
        if (!moduleState && loading) {
          // Keep the loading state to avoid flickering
        } else if (!moduleState) {
          setLoading(true);
        }

        const response = await getModuleState(moduleName);
        setModuleState(response.data);
        setError(null);
      } catch (err) {
        setError(`Failed to fetch state for ${moduleName}. Is the core service running?`);
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

    // Cleanup function to prevent memory leaks
    return () => clearInterval(intervalId);
  }, [data_source_api, moduleState]);

  const toggleDropdown = () => {
    setIsDropdownOpen(!isDropdownOpen);
  };

  const selectView = (index) => {
    setActiveViewIndex(index);
    setIsDropdownOpen(false);
  };

  const handleQueryExecuted = async () => {
    console.log('SwitchableView handleQueryExecuted called');
    
    // Find the "Last Query Result" view
    const lastQueryResultIndex = views.findIndex(view => 
      view.title === "Last Query Result"
    );
    console.log('Found Last Query Result index:', lastQueryResultIndex);
    
    if (lastQueryResultIndex !== -1) {
      // Immediately refresh the module state to get the latest query results
      const moduleName = data_source_api?.split('/')[3];
      console.log('Module name for refresh:', moduleName);
      
      if (moduleName) {
        try {
          console.log('Fetching updated module state...');
          
          // Add a longer delay to ensure the backend has processed the query
          await new Promise(resolve => setTimeout(resolve, 500));
          
          const response = await getModuleState(moduleName);
          console.log('Got updated module state:', response.data);
          
          // Validate that we have query result data
          const hasQueryResult = response.data?.last_query_result && 
                                (response.data.last_query_result.rows || response.data.last_query_result.columns);
          
          if (hasQueryResult) {
            console.log('Query result data found, updating state and switching view');
            setModuleState(response.data);
            setActiveViewIndex(lastQueryResultIndex);
          } else {
            console.warn('No query result data found, retrying...');
            // Retry once more with a longer delay
            await new Promise(resolve => setTimeout(resolve, 1000));
            const retryResponse = await getModuleState(moduleName);
            console.log('Retry response:', retryResponse.data);
            setModuleState(retryResponse.data);
            setActiveViewIndex(lastQueryResultIndex);
          }
        } catch (err) {
          console.error('Failed to refresh module state after query execution:', err);
          // Still switch to the view even if refresh failed
          setActiveViewIndex(lastQueryResultIndex);
        }
      } else {
        // No module name, just switch views
        setActiveViewIndex(lastQueryResultIndex);
      }
    }
  };

  const handleRowClick = (item) => {
    setSelectedItem(item);
    setShowPopout(true);
  };
  
  const handleClosePopout = () => {
    setShowPopout(false);
    setSelectedItem(null);
  };

  const handleEmailCreated = async (newEmail) => {
    // Show the new email in the popout
    setSelectedItem(newEmail);
    setShowPopout(true);
    
    // Refresh the module state to show the new draft
    const moduleName = data_source_api?.split('/')[3];
    if (moduleName) {
      try {
        const refreshResponse = await getModuleState(moduleName);
        setModuleState(refreshResponse.data);
      } catch (err) {
        console.error('Failed to refresh module state after creating draft:', err);
      }
    }
  };

  const renderActiveView = () => {
    if (!views || views.length === 0) return null;
    
    const activeView = views[activeViewIndex];
    const viewProps = {
      ...activeView,
      module_id,
      data_source_api,
      // Pass the view title to the component
      title: activeView.title,
      // Add a key to prevent unnecessary re-renders
      key: `${module_id}-view-${activeViewIndex}`,
      // Pass the shared module state to avoid duplicate fetching
      moduleState: moduleState
    };

    // Add row click handler for email module
    if (module_id === 'email') {
      viewProps.onRowClick = handleRowClick;
    }

    switch (activeView.component_type) {
      case 'table':
        return <GenericTable {...viewProps} />;
      case 'key_value':
      case 'key_value_viewer':
        return <GenericKeyValue {...viewProps} />;
      case 'file_tree':
        return <GenericFileTree {...viewProps} />;
      case 'query_executor':
        return <QueryExecutor {...viewProps} onQueryExecuted={handleQueryExecuted} />;
      default:
        return <div className="error-message">Unknown component type: {activeView.component_type}</div>;
    }
  };

  const activeView = views && views.length > 0 ? views[activeViewIndex] : null;
  const activeTitle = activeView?.title || title;

  return (
    <div 
      className={`module-container ${sizeClass}`} 
      data-module-id={module_id}
    >
      <div className="switchable-view-header">
        <h2>{activeTitle}</h2>
        <div className="header-actions">
          {/* Create Email Button - only show for email module */}
          {module_id === 'email' && (
            <CreateEmailButton onEmailCreated={handleEmailCreated} />
          )}
          
          {/* View Selector */}
          {views && views.length > 1 && (
          <div className="view-selector">
            <button 
              className="view-selector-button" 
              onClick={toggleDropdown}
              aria-label="Switch view"
            >
              <span className="view-selector-icon">▼</span>
            </button>
            {isDropdownOpen && (
              <div className="view-selector-dropdown">
                {views.map((view, index) => (
                  <button
                    key={index}
                    className={`view-option ${index === activeViewIndex ? 'active' : ''}`}
                    onClick={() => selectView(index)}
                  >
                    {view.title}
                  </button>
                ))}
              </div>
            )}
          </div>
          )}
        </div>
      </div>
      {activeView?.description && (
        <p className="component-description">{activeView.description}</p>
      )}
      <div className="module-content">
        {loading ? (
          <p>Loading...</p>
        ) : error ? (
          <p className="error-message">{error}</p>
        ) : (
          renderActiveView()
        )}
      </div>
      
      {/* Email popout for email module */}
      {module_id === 'email' && showPopout && selectedItem && (
        <EmailPopout 
          email={selectedItem} 
          onClose={handleClosePopout} 
        />
      )}
    </div>
  );
};

export default SwitchableView;