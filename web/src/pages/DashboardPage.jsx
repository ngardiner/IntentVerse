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

  const renderComponent = (moduleSchema) => {
    // This function acts as a factory, returning the correct
    // generic component based on the schema from the backend.
    
    // Determine the size class based on the module's size property
    const getSizeClass = (size, moduleId) => {
      switch (size) {
        case 'small': return 'size-small';
        case 'medium': return 'size-medium';
        case 'large': return 'size-large';
        case 'xlarge': return 'size-xlarge';
        default: return ''; // Default size
      }
    };
    
    // Get grid row style if specified
    const getGridRowStyle = (component, moduleId) => {
      // Special handling for database widgets to prevent overlap
      // Default behavior
      if (component.grid_row !== undefined) {
        return { gridRow: `${component.grid_row}` };
      }
      return {};
    };

    // If the module has components array, check if we should use SwitchableView
    if (moduleSchema.components && Array.isArray(moduleSchema.components)) {
      // Check for switchable_group component type
      const switchableGroupComponent = moduleSchema.components.find(
        component => component.component_type === 'switchable_group'
      );
      
      if (switchableGroupComponent) {
        // Process each switchable_group component
        const regularComponents = moduleSchema.components.filter(
          component => component.component_type !== 'switchable_group'
        );
        
        // Render switchable groups and regular components
        return [
          // Render switchable groups
          ...moduleSchema.components
            .filter(component => component.component_type === 'switchable_group')
            .map(component => {
              const sizeClass = getSizeClass(component.size || 'small', moduleSchema.module_id);
              return (
                <SwitchableView
                  key={`${moduleSchema.module_id}-${component.title}`}
                  title={component.title}
                  module_id={moduleSchema.module_id || moduleSchema.name}
                  data_source_api={component.views[0]?.data_source_api}
                  views={component.views}
                  sizeClass={sizeClass}
                />
              );
            }),
          
          // Render regular components
          ...regularComponents.map(component => {
            const sizeClass = getSizeClass(component.size || moduleSchema.size, moduleSchema.module_id);
            const props = {
              key: `${moduleSchema.module_id || moduleSchema.name}-${component.component_type}-${component.title}`,
              title: component.title || moduleSchema.display_name,
              ...component,
              module_id: moduleSchema.module_id || moduleSchema.name,
              sizeClass
            };

            const gridRowStyle = getGridRowStyle(component, moduleSchema.module_id);
            
            switch (component.component_type) {
              case 'file_tree':
                return <div style={gridRowStyle}><GenericFileTree {...props} /></div>;
              case 'table':
                return (
                  <div style={gridRowStyle}>
                    <GenericTable 
                      {...props} 
                      data_path={component.data_path}
                      dynamic_columns={component.dynamic_columns}
                      max_rows={component.max_rows}
                    />
                  </div>
                );
              case 'key_value_viewer':
              case 'key_value':
                return (
                  <div style={gridRowStyle}>
                    <GenericKeyValue 
                      {...props} 
                      data_path={component.data_path}
                      display_as={component.display_as}
                      language={component.language}
                    />
                  </div>
                );
              default:
                return (
                  <div key={props.key} className={`module-container ${sizeClass}`} style={gridRowStyle}>
                    <h2>{props.title}</h2>
                    <p className="error-message">Unknown component type: {component.component_type}</p>
                  </div>
                );
            }
          })
        ];
      }
      
      // Check if this is a module that should use SwitchableView for all components
      if (moduleSchema.module_id === 'web_search' || moduleSchema.module_id === 'email' || moduleSchema.use_switchable_view) {
        const sizeClass = getSizeClass(moduleSchema.size || 'large', moduleSchema.module_id); // Double the size
        return (
          <SwitchableView
            key={moduleSchema.module_id || moduleSchema.name}
            title={moduleSchema.display_name}
            module_id={moduleSchema.module_id || moduleSchema.name}
            data_source_api={moduleSchema.components[0]?.data_source_api}
            views={moduleSchema.components}
            sizeClass={sizeClass}
          />
        );
      }
      
      // Otherwise, render each component separately
      return moduleSchema.components.map((component) => {
        const sizeClass = getSizeClass(component.size || moduleSchema.size, moduleSchema.module_id);
        const props = {
          key: `${moduleSchema.module_id || moduleSchema.name}-${component.component_type}`,
          title: component.title || moduleSchema.display_name,
          ...component,
          module_id: moduleSchema.module_id || moduleSchema.name,
          sizeClass
        };

        const gridRowStyle = getGridRowStyle(component, moduleSchema.module_id);
        
        switch (component.component_type) {
          case 'file_tree':
            return <div style={gridRowStyle}><GenericFileTree {...props} /></div>;
          case 'table':
            return (
              <div style={gridRowStyle}>
                <GenericTable 
                  {...props} 
                  data_path={component.data_path}
                  dynamic_columns={component.dynamic_columns}
                  max_rows={component.max_rows}
                />
              </div>
            );
          case 'key_value_viewer':
          case 'key_value':
            return (
              <div style={gridRowStyle}>
                <GenericKeyValue 
                  {...props} 
                  data_path={component.data_path}
                  display_as={component.display_as}
                  language={component.language}
                />
              </div>
            );
          default:
            return (
              <div key={props.key} className={`module-container ${sizeClass}`} style={gridRowStyle}>
                <h2>{props.title}</h2>
                <p className="error-message">Unknown component type: {component.component_type}</p>
              </div>
            );
        }
      });
    }
    
    // Fallback for modules without components array
    const sizeClass = getSizeClass(moduleSchema.size, moduleSchema.module_id);
    const props = {
      key: moduleSchema.module_id || moduleSchema.name,
      title: moduleSchema.display_name,
      ...moduleSchema,
      sizeClass
    };

    const gridRowStyle = getGridRowStyle(moduleSchema, moduleSchema.module_id);
    
    switch (moduleSchema.component_type) {
      case 'file_tree':
        return <div style={gridRowStyle}><GenericFileTree {...props} /></div>;
      case 'table':
        return (
          <div style={gridRowStyle}>
            <GenericTable 
              {...props} 
              data_path={moduleSchema.data_path}
              dynamic_columns={moduleSchema.dynamic_columns}
              max_rows={moduleSchema.max_rows}
            />
          </div>
        );
      case 'key_value_viewer':
      case 'key_value':
        return (
          <div style={gridRowStyle}>
            <GenericKeyValue 
              {...props} 
              data_path={moduleSchema.data_path}
              display_as={moduleSchema.display_as}
              language={moduleSchema.language}
            />
          </div>
        );
      default:
        return (
          <div key={moduleSchema.module_id || moduleSchema.name} className={`module-container ${sizeClass}`} style={gridRowStyle}>
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