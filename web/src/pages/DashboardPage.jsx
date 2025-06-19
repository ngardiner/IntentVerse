import React, { useState, useEffect } from 'react';
import { getUILayout } from '../api/client';

// Import the actual generic components
import GenericFileTree from '../components/generic/GenericFileTree';
import GenericTable from '../components/generic/GenericTable';
import GenericKeyValue from '../components/generic/GenericKeyValue';

const DashboardPage = () => {
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

  const renderComponent = (moduleSchema) => {
    // This function acts as a factory, returning the correct
    // generic component based on the schema from the backend.
    
    // If the module has components array, render each component
    if (moduleSchema.components && Array.isArray(moduleSchema.components)) {
      return moduleSchema.components.map((component) => {
        const props = {
          key: `${moduleSchema.module_id || moduleSchema.name}-${component.component_type}`,
          title: component.title || moduleSchema.display_name,
          ...component,
          module_id: moduleSchema.module_id || moduleSchema.name
        };

        switch (component.component_type) {
          case 'file_tree':
            return <GenericFileTree {...props} />;
          case 'table':
            return <GenericTable {...props} />;
          case 'key_value_viewer':
          case 'key_value':
            return <GenericKeyValue {...props} />;
          default:
            return (
              <div key={props.key} className="module-container">
                <h2>{props.title}</h2>
                <p className="error-message">Unknown component type: {component.component_type}</p>
              </div>
            );
        }
      });
    }
    
    // Fallback for modules without components array
    const props = {
      key: moduleSchema.module_id || moduleSchema.name,
      title: moduleSchema.display_name,
      ...moduleSchema
    };

    switch (moduleSchema.component_type) {
      case 'file_tree':
        return <GenericFileTree {...props} />;
      case 'table':
        return <GenericTable {...props} />;
      case 'key_value_viewer':
      case 'key_value':
        return <GenericKeyValue {...props} />;
      default:
        return (
          <div key={moduleSchema.module_id || moduleSchema.name} className="module-container">
            <h2>{moduleSchema.display_name}</h2>
            <p className="error-message">Unknown component type: {moduleSchema.component_type}</p>
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
      {/* Modules Grid */}
      <div className="modules-grid">
        {layout.length > 0 ? (
          layout.flatMap(moduleSchema => {
            const rendered = renderComponent(moduleSchema);
            // Handle both arrays of components and single components
            return Array.isArray(rendered) ? rendered : [rendered];
          })
        ) : (
          <p>No modules were loaded by the Core Engine.</p>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;