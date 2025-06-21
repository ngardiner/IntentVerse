import React, { useState, useEffect } from 'react';
import { getModuleState } from '../../api/client';
import GenericTable from './GenericTable';
import GenericKeyValue from './GenericKeyValue';
import GenericFileTree from './GenericFileTree';
import EmailPopout from './EmailPopout';

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
        // Don't show loading spinner on background polls
        if (!moduleState) setLoading(true);

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

    fetchState(); // Initial fetch
    
    // Set up an interval to poll for updates every 3 seconds
    const intervalId = setInterval(fetchState, 3000);

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

  const handleRowClick = (item) => {
    setSelectedItem(item);
    setShowPopout(true);
  };
  
  const handleClosePopout = () => {
    setShowPopout(false);
    setSelectedItem(null);
  };

  const renderActiveView = () => {
    if (!views || views.length === 0) return null;
    
    const activeView = views[activeViewIndex];
    const viewProps = {
      ...activeView,
      module_id,
      data_source_api,
      // Don't pass title as we're handling it in this component
      title: undefined,
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
      default:
        return <div className="error-message">Unknown component type: {activeView.component_type}</div>;
    }
  };

  const activeView = views && views.length > 0 ? views[activeViewIndex] : null;
  const activeTitle = activeView?.title || title;

  return (
    <div className={`module-container ${sizeClass}`}>
      <div className="switchable-view-header">
        <h2>{activeTitle}</h2>
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