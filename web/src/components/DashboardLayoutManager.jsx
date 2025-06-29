import React, { useState, useEffect } from 'react';

const DashboardLayoutManager = ({ 
  isEditing, 
  onSaveLayout, 
  onCancelEdit,
  children,
  currentDashboard
}) => {
  // Helper function to convert size class to column span
  const getSizeSpan = (sizeClass) => {
    switch (sizeClass) {
      case 'size-small': return 3;
      case 'size-medium': return 6;
      case 'size-large': return 9;
      case 'size-xlarge': return 12;
      default: return 4; // Default size (1/3 of grid)
    }
  };
  // State to track the original and current layout
  const [originalLayout, setOriginalLayout] = useState({});
  const [currentLayout, setCurrentLayout] = useState({});
  const [hiddenWidgets, setHiddenWidgets] = useState({});
  const [originalHiddenState, setOriginalHiddenState] = useState({});
  const [isDragging, setIsDragging] = useState(false);
  const [draggedItem, setDraggedItem] = useState(null);
  
  // Generate an initial layout based on the children's natural flow
  const generateInitialLayout = () => {
    const layout = {};
    let currentRow = 1;
    let currentCol = 1;
    
    // Process each child to create an initial layout
    React.Children.forEach(children, child => {
      if (!child) return;
      
      // Extract the module ID from the child's props
      const moduleId = child.props?.module_id || 
                      child.props?.moduleSchema?.module_id || 
                      (child.props?.moduleSchema && `module-${child.props.moduleSchema.module_id}`) ||
                      child.key;
      
      if (!moduleId) return;
      
      // Get the size span for this module
      const sizeClass = child.props?.sizeClass || '';
      const colSpan = getSizeSpan(sizeClass);
      
      // If this module won't fit on the current row, move to the next row
      if (currentCol + colSpan - 1 > 12) {
        currentRow++;
        currentCol = 1;
      }
      
      // Add this module to the layout
      layout[moduleId] = {
        row: currentRow,
        col: currentCol
      };
      
      // Update the current column position
      currentCol += colSpan;
      
      // If we've reached the end of the row, move to the next row
      if (currentCol > 12) {
        currentRow++;
        currentCol = 1;
      }
    });
    
    return layout;
  };

  // Load the saved layout from localStorage when the component mounts or dashboard changes
  useEffect(() => {
    // Always generate the layout based on current children first.
    // This gives us a complete default for every widget.
    const generatedLayout = generateInitialLayout();
    
    // Initialize hidden widgets based on children props
    const initialHiddenState = {};
    React.Children.forEach(children, child => {
      if (!child) return;
      
      // Extract the module ID from the child's props
      const moduleId = child.props?.module_id || 
                      child.props?.moduleSchema?.module_id || 
                      (child.props?.moduleSchema && `module-${child.props.moduleSchema.module_id}`) ||
                      child.key;
      
      if (!moduleId) return;
      
      // Check if this widget should be hidden by default
      if (child.props?.hidden || child.props?.moduleSchema?.hidden) {
        initialHiddenState[moduleId] = true;
      }
    });

    const savedLayoutJSON = localStorage.getItem(`dashboard-layout-${currentDashboard}`);
    const savedHiddenJSON = localStorage.getItem(`dashboard-hidden-${currentDashboard}`);

    // Process saved layout
    let mergedLayout = { ...generatedLayout };
    if (savedLayoutJSON) {
      try {
        const savedLayout = JSON.parse(savedLayoutJSON);

        // Create a new layout that is guaranteed to be complete.
        // Start with the complete generated layout.
        // Then, overwrite with any valid positions from the saved layout.
        Object.keys(mergedLayout).forEach(moduleId => {
          if (savedLayout[moduleId] && savedLayout[moduleId].row && savedLayout[moduleId].col) {
            mergedLayout[moduleId] = savedLayout[moduleId];
          }
        });
      } catch (e) {
        console.error("Error parsing saved layout, falling back to default:", e);
      }
    }
    
    // Process saved hidden state
    let mergedHiddenState = { ...initialHiddenState };
    if (savedHiddenJSON) {
      try {
        const savedHidden = JSON.parse(savedHiddenJSON);
        mergedHiddenState = { ...initialHiddenState, ...savedHidden };
      } catch (e) {
        console.error("Error parsing saved hidden state, falling back to default:", e);
      }
    }

    setCurrentLayout(mergedLayout);
    setHiddenWidgets(mergedHiddenState);
    
    if (!isEditing) {
      setOriginalLayout(mergedLayout);
      setOriginalHiddenState(mergedHiddenState);
    }
  }, [currentDashboard, isEditing, children]);

  // When entering edit mode, store the original layout and hidden state
  useEffect(() => {
    if (isEditing) {
      setOriginalLayout({...currentLayout});
      setOriginalHiddenState({...hiddenWidgets});
    }
  }, [isEditing]);
  
  // Handle saving the layout
  const handleSaveLayout = () => {
    localStorage.setItem(`dashboard-layout-${currentDashboard}`, JSON.stringify(currentLayout));
    localStorage.setItem(`dashboard-hidden-${currentDashboard}`, JSON.stringify(hiddenWidgets));
    onSaveLayout();
  };
  
  // Handle canceling edits
  const handleCancelEdit = () => {
    setCurrentLayout({...originalLayout});
    setHiddenWidgets({...originalHiddenState});
    onCancelEdit();
  };
  
  // State for screen reader announcements
  const [announcement, setAnnouncement] = useState('');

  // Toggle widget visibility
  const toggleWidgetVisibility = (moduleId) => {
    console.log('Toggling visibility for:', moduleId, 'Current state:', hiddenWidgets[moduleId]);
    const wasHidden = hiddenWidgets[moduleId];
    setHiddenWidgets(prev => ({
      ...prev,
      [moduleId]: !prev[moduleId]
    }));
    
    // Announce the change to screen readers
    setAnnouncement(wasHidden ? `Widget ${moduleId} shown` : `Widget ${moduleId} hidden`);
    setTimeout(() => setAnnouncement(''), 1000);
  };
  
  // Update the position of a module
  const updateModulePosition = (moduleId, position) => {
    setCurrentLayout(prev => ({
      ...prev,
      [moduleId]: position
    }));
  };
  
  // Handle drag start
  const handleDragStart = (e, moduleId) => {
    if (!isEditing) return;
    
    setIsDragging(true);
    setDraggedItem(moduleId);
    
    // Add a class to the body to indicate dragging
    document.body.classList.add('dragging-module');
    
    // Get the module element
    const moduleElement = e.currentTarget;
    
    // Add a class to highlight the module being dragged
    moduleElement.classList.add('dragging');
    
    // Set ghost image (optional)
    const dragImage = document.createElement('div');
    dragImage.textContent = 'Moving Module';
    dragImage.style.position = 'absolute';
    dragImage.style.top = '-1000px';
    document.body.appendChild(dragImage);
    
    // Check if setDragImage is available (not available in some test environments)
    if (e.dataTransfer.setDragImage) {
      e.dataTransfer.setDragImage(dragImage, 0, 0);
    }
    
    // Clean up after drag image is set
    setTimeout(() => {
      if (document.body.contains(dragImage)) {
        document.body.removeChild(dragImage);
      }
    }, 0);
    
    // Make sure the dataTransfer object has the moduleId
    e.dataTransfer.setData('text/plain', moduleId);
  };
  
  // Handle drag over
  const handleDragOver = (e, row, col) => {
    if (!isEditing || !isDragging) return;
    e.preventDefault();
    
    // Set the dropEffect to move
    e.dataTransfer.dropEffect = 'move';
    
    // Highlight the drop target
    e.currentTarget.classList.add('drag-over');
  };
  
  // Handle drag leave
  const handleDragLeave = (e) => {
    if (!isEditing || !isDragging) return;
    
    // Remove highlight from the drop target
    e.currentTarget.classList.remove('drag-over');
  };
  
  // Handle drop
  const handleDrop = (e, row, col) => {
    if (!isEditing || !isDragging || !draggedItem) return;
    
    e.preventDefault();
    
    // Remove highlight from the drop target
    e.currentTarget.classList.remove('drag-over');
    
    // Update the position of the dragged module
    updateModulePosition(draggedItem, { row, col });
    
    // Remove the dragging class from all module wrappers
    const draggingElements = document.querySelectorAll('.module-wrapper.dragging');
    draggingElements.forEach(element => {
      element.classList.remove('dragging');
    });
    
    // Reset drag state
    setIsDragging(false);
    setDraggedItem(null);
    
    // Remove the dragging class from the body
    document.body.classList.remove('dragging-module');
  };
  
  // Handle drag end
  const handleDragEnd = () => {
    if (!isEditing) return;
    
    // Remove the dragging class from all module wrappers
    const draggingElements = document.querySelectorAll('.module-wrapper.dragging');
    draggingElements.forEach(element => {
      element.classList.remove('dragging');
    });
    
    // Reset drag state
    setIsDragging(false);
    setDraggedItem(null);
    
    // Remove the dragging class from the body
    document.body.classList.remove('dragging-module');
  };
  
  // Render the layout manager UI
  return (
    <div className="dashboard-layout-manager">
      {/* Screen reader announcements */}
      <div role="status" aria-live="polite" className="sr-only">
        {announcement}
      </div>
      {isEditing && (
        <div className="layout-edit-controls">
          <div className="layout-edit-message">
            <span>Editing Dashboard Layout</span>
            <p className="layout-edit-instructions">
              Drag and drop modules to rearrange them. Use the eye icon to show/hide widgets.
            </p>
          </div>
          <div className="layout-edit-actions">
            <button className="layout-save-button" onClick={handleSaveLayout} aria-label="Save layout changes">
              Save Layout
            </button>
            <button className="layout-cancel-button" onClick={handleCancelEdit} aria-label="Cancel layout changes">
              Cancel
            </button>
            <button className="layout-reset-button" onClick={() => {
              setCurrentLayout({...originalLayout});
              setHiddenWidgets({...originalHiddenState});
            }} aria-label="Reset layout to default">
              Reset to Default
            </button>
          </div>
        </div>
      )}
      
      {isEditing && (
        <div className="hidden-widgets-panel">
          <h3>Hidden Widgets ({Object.keys(hiddenWidgets).filter(id => hiddenWidgets[id]).length})</h3>
          {/* Debug info */}
          <div style={{fontSize: '0.7rem', color: 'var(--text-color-secondary)', marginBottom: '0.5rem'}}>
            Debug: All widgets: {JSON.stringify(Object.keys(hiddenWidgets))} | Hidden: {JSON.stringify(Object.keys(hiddenWidgets).filter(id => hiddenWidgets[id]))}
          </div>
          <div className="hidden-widgets-list">
            {(() => {
              const hiddenItems = [];
              
              // Process all children to find hidden widgets
              React.Children.forEach(children, child => {
                if (!child) return;
                
                // Handle both single components and arrays of components
                const processChild = (childComponent) => {
                  if (!childComponent) return;
                  
                  const moduleId = childComponent.props?.module_id || 
                                  childComponent.props?.moduleSchema?.module_id || 
                                  (childComponent.props?.moduleSchema && `module-${childComponent.props.moduleSchema.module_id}`) ||
                                  childComponent.key;
                  
                  if (moduleId && hiddenWidgets[moduleId]) {
                    const title = childComponent.props?.title || 
                                 childComponent.props?.moduleSchema?.title || 
                                 childComponent.props?.display_name ||
                                 moduleId;
                    
                    hiddenItems.push(
                      <div key={moduleId} className="hidden-widget-item">
                        <span className="hidden-widget-title">{title}</span>
                        <button 
                          className="show-widget-button"
                          onClick={() => toggleWidgetVisibility(moduleId)}
                          title="Show widget"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 6a7 7 0 017 7 7 7 0 01-7 7 7 7 0 01-7-7 7 7 0 017-7zm0 3a4 4 0 100 8 4 4 0 000-8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                          Show
                        </button>
                      </div>
                    );
                  }
                };
                
                // Handle arrays of components
                if (Array.isArray(child)) {
                  child.forEach(processChild);
                } else {
                  processChild(child);
                }
              });
              
              return hiddenItems.length > 0 ? hiddenItems : (
                <p className="no-hidden-widgets">No hidden widgets</p>
              );
            })()}
          </div>
        </div>
      )}
      
      <div className={`modules-grid ${isEditing ? 'editing' : ''}`}>
        {React.Children.map(children, child => {
          if (!child) return null;
          
          // Extract the module ID from the child's props
          const moduleId = child.props?.module_id || 
                          child.props?.moduleSchema?.module_id || 
                          (child.props?.moduleSchema && `module-${child.props.moduleSchema.module_id}`) ||
                          child.key;
          
          if (!moduleId) return child;
          
          // Get the position for this module from the current layout
          const position = currentLayout[moduleId] || {};
          
          // Create grid style for positioning
          const gridStyle = {
            gridRow: position.row ? `${position.row}` : 'auto',
            gridColumn: position.col ? `${position.col} / span ${getSizeSpan(child.props?.sizeClass)}` : 'auto'
          };
          
          // Skip rendering if widget is hidden (both in edit and normal mode to prevent overlap)
          if (hiddenWidgets[moduleId]) {
            return null;
          }
          
          // If in edit mode, add drag and drop handlers
          const editProps = isEditing ? {
            onDragStart: (e) => {
              // Prevent dragging if the target is a control button
              if (e.target.closest('.module-control-buttons')) {
                e.preventDefault();
                return;
              }
              handleDragStart(e, moduleId);
            },
            onDragEnd: handleDragEnd,
            className: `module-wrapper ${isEditing ? 'editing' : ''} ${draggedItem === moduleId ? 'dragging' : ''} ${hiddenWidgets[moduleId] ? 'hidden-widget' : ''}`,
          } : {};
          
          // Wrap the child in a div with the appropriate grid positioning
          return (
            <div 
              style={gridStyle}
              className={editProps.className}
              draggable={isEditing}
              onDragStart={editProps.onDragStart}
              onDragEnd={editProps.onDragEnd}
            >
              {isEditing && (
                <div className="module-edit-controls">
                  <div className="module-drag-handle" title="Drag to move widget">⋮⋮</div>
                  <div className="module-control-buttons">
                    <button 
                      className={`module-visibility-toggle ${hiddenWidgets[moduleId] ? 'hidden' : 'visible'}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleWidgetVisibility(moduleId);
                      }}
                      title={hiddenWidgets[moduleId] ? "Show widget" : "Hide widget"}
                    >
                      {hiddenWidgets[moduleId] ? (
                        <>
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M3 3L21 21M10.5 10.677a2 2 0 002.823 2.823M7.362 7.561A7 7 0 0112 6c3.866 0 7 3.134 7 7 0 1.572-.518 3.02-1.39 4.185M15 15.73A7 7 0 015.268 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                          Show
                        </>
                      ) : (
                        <>
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 6a7 7 0 017 7 7 7 0 01-7 7 7 7 0 01-7-7 7 7 0 017-7zm0 3a4 4 0 100 8 4 4 0 000-8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                          Hide
                        </>
                      )}
                    </button>
                    <span className="widget-title-label">{child.props?.title || child.props?.moduleSchema?.title || moduleId}</span>
                  </div>
                </div>
              )}
              {child}
            </div>
          );
        })}
        
        {/* If in edit mode, render drop zones */}
        {isEditing && (
          <div className="drop-zones-overlay">
            {Array.from({ length: 10 }).map((_, rowIndex) => (
              // Create drop zones at all column positions for better flexibility
              [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((colStart) => (
                <div 
                  key={`drop-${rowIndex}-${colStart}`}
                  className={`drop-zone`}
                  onDragOver={(e) => handleDragOver(e, rowIndex + 1, colStart)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, rowIndex + 1, colStart)}
                  style={{
                    gridRow: rowIndex + 1,
                    gridColumn: colStart,
                    width: '30px',
                    height: '60px',
                    minHeight: '60px'
                  }}
                />
              ))
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardLayoutManager;