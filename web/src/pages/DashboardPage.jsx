import React, { useState, useEffect } from 'react';
import { getUILayout } from '../api/client';

// Import the actual generic components
import GenericFileTree from '../components/generic/GenericFileTree';
import GenericTable from '../components/generic/GenericTable';
import GenericKeyValue from '../components/generic/GenericKeyValue';
import SwitchableView from '../components/generic/SwitchableView';
import DashboardLayoutManager from '../components/DashboardLayoutManager';

const DashboardPage = ({ isEditing, onSaveLayout, onCancelEdit, currentDashboard }) => {
  const [layout, setLayout] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // useEffect hook to fetch data when the component mounts
  useEffect(() => {
    const fetchLayout = async () => {
      try {
        setLoading(true);
        const response = await getUILayout();
        const modules = response.data.modules || [];
        setLayout(modules);
        setError(null);
      } catch (err) {
        setError("Failed to fetch UI layout from the server. Please ensure the core service is running.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchLayout();
  }, []); // The empty dependency array ensures this runs only once on mount

  const renderComponent = (schemaItem) => {
    // This function acts as a factory, returning the correct
    // generic component based on the schema from the backend.

    // Determine the size class based on the schema item's size property
    const getSizeClass = (size) => {
      switch (size) {
        case 'small': return 'size-small';
        case 'medium': return 'size-medium';
        case 'large': return 'size-large';
        case 'xlarge': return 'size-xlarge';
        default: return ''; // Default size
      }
    };

    // Get grid row style if specified
    const getGridRowStyle = (item) => {
      if (item.grid_row !== undefined) {
        return { gridRow: `${item.grid_row}` };
      }
      return {};
    };

    // --- Core Logic for Handling Module Schema Structure ---
    // If this schemaItem has a 'components' array and is NOT a 'switchable_group' itself,
    // then it means it's a module (like 'database') that contains multiple top-level components
    // that need to be rendered separately on the dashboard.
    if (schemaItem.components && Array.isArray(schemaItem.components) && schemaItem.component_type !== 'switchable_group') {
      // Return an array of rendered components by recursively calling renderComponent for each sub-component.
      // We pass the parent module_id to the sub-component's props for context, and add a unique key index.
      return schemaItem.components.map((subComponent, index) => {
        const uniqueModuleId = `${schemaItem.module_id}-${index}`;
        const subComponentWithParentContext = {
            ...subComponent,
            module_id: uniqueModuleId, // Use the new unique ID
            _unique_key_index: index // For unique React keys when mapping
        };
        return renderComponent(subComponentWithParentContext);
      });
    }

    // Otherwise, render a single component based on its component_type.
    // This covers:
    // 1. Modules with a single top-level component_type (e.g., File System, Memory after schema updates).
    // 2. Individual sub-components within a 'components' array that were passed recursively (e.g., the individual switchable_group items for Database).
    const sizeClass = getSizeClass(schemaItem.size);
    const props = {
      // Key generation: Use module_id for key if available, otherwise a generated key for nested components
      key: schemaItem.module_id || `${schemaItem.title || 'untitled'}-${schemaItem.component_type || 'unknown'}-${schemaItem._unique_key_index || 0}`,
      title: schemaItem.title || schemaItem.display_name,
      ...schemaItem, // Pass all properties of the current schema item
      module_id: schemaItem.module_id || schemaItem.name, // Ensure module_id is passed, falls back to name
      sizeClass,
      hidden: schemaItem.hidden // Pass the hidden property
    };

    const gridRowStyle = getGridRowStyle(schemaItem);

    switch (schemaItem.component_type) {
      case 'file_tree':
        return <GenericFileTree {...props} />;
      case 'table':
        return (
          <GenericTable
            {...props}
            data_path={schemaItem.data_path}
            dynamic_columns={schemaItem.dynamic_columns}
            max_rows={schemaItem.max_rows}
          />
        );
      case 'key_value_viewer':
      case 'key_value':
        return (
          <GenericKeyValue
            {...props}
            data_path={schemaItem.data_path}
            display_as={schemaItem.display_as}
            language={schemaItem.language}
          />
        );
      case 'switchable_group':
        return (
          <SwitchableView
            key={props.key}
            title={props.title}
            module_id={props.module_id}
            data_source_api={(schemaItem.views && schemaItem.views[0]?.data_source_api) || (schemaItem.components && schemaItem.components[0]?.data_source_api)} // RE-ADDED AND MADE ROBUST
            views={schemaItem.views || schemaItem.components} // Use 'views' if explicitly defined, fallback to 'components' array
            sizeClass={sizeClass}
          />
        );
      default:
        return (
          <div key={props.key} className={`module-container ${sizeClass}`} style={gridRowStyle}>
            <h2>{props.title}</h2>
            <p className="error-message">Unknown component type: {schemaItem.component_type}</p>
          </div>
        );
    }
  };

  if (loading) {
    return <div className="dashboard-container"><h1>Loading Dashboard...</h1></div>;
  }

  if (error) {
    return <div className="dashboard-container"><p className="error-message">{error}</p></div>;
  }

  return (
    <div className="dashboard-container">
      {/* Modules Grid with Layout Manager */}
      <DashboardLayoutManager
        isEditing={isEditing}
        onSaveLayout={onSaveLayout}
        onCancelEdit={onCancelEdit}
        currentDashboard={currentDashboard}
      >
        {layout.length > 0 ? (
          layout.flatMap(moduleSchema => {
            const rendered = renderComponent(moduleSchema);
            // Handle both arrays of components and single components
            return Array.isArray(rendered) ? rendered : [rendered];
          })
        ) : (
          <p>No modules were loaded by the Core Engine.</p>
        )}
      </DashboardLayoutManager>
    </div>
  );
};

export default DashboardPage;