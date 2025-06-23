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

    const savedLayoutJSON = localStorage.getItem(`dashboard-layout-${currentDashboard}`);

    if (savedLayoutJSON) {
      try {
        const savedLayout = JSON.parse(savedLayoutJSON);

        // Create a new layout that is guaranteed to be complete.
        // Start with the complete generated layout.
        // Then, overwrite with any valid positions from the saved layout.
        const mergedLayout = { ...generatedLayout };
        Object.keys(mergedLayout).forEach(moduleId => {
          if (savedLayout[moduleId] && savedLayout[moduleId].row && savedLayout[moduleId].col) {
            mergedLayout[moduleId] = savedLayout[moduleId];
          }
        });

        setCurrentLayout(mergedLayout);
        if (!isEditing) {
          setOriginalLayout(mergedLayout);
        }
      } catch (e) {
        console.error("Error parsing saved layout, falling back to default:", e);
        // If parsing fails, just use the fresh generated layout.
        setCurrentLayout(generatedLayout);
        if (!isEditing) {
          setOriginalLayout(generatedLayout);
        }
      }
    } else {
      // If no saved layout exists, use the fresh generated layout.
      setCurrentLayout(generatedLayout);
      if (!isEditing) {
        setOriginalLayout(generatedLayout);
      }
    }
  }, [currentDashboard, isEditing, children]);

  // When entering edit mode, store the original layout
  useEffect(() => {
    if (isEditing) {
      setOriginalLayout({...currentLayout});
    }
  }, [isEditing]);
  
  // Handle saving the layout
  const handleSaveLayout = () => {
    localStorage.setItem(`dashboard-layout-${currentDashboard}`, JSON.stringify(currentLayout));
    onSaveLayout();
  };
  
  // Handle canceling edits
  const handleCancelEdit = () => {
    setCurrentLayout({...originalLayout});
    onCancelEdit();
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
    e.dataTransfer.setDragImage(dragImage, 0, 0);
    
    // Clean up after drag image is set
    setTimeout(() => {
      document.body.removeChild(dragImage);
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
    
    // Reset drag state
    setIsDragging(false);
    setDraggedItem(null);
    
    // Remove the dragging class from the body
    document.body.classList.remove('dragging-module');
  };
  
  // Handle drag end
  const handleDragEnd = () => {
    if (!isEditing) return;
    
    // Reset drag state
    setIsDragging(false);
    setDraggedItem(null);
    
    // Remove the dragging class from the body
    document.body.classList.remove('dragging-module');
  };
  
  // Render the layout manager UI
  return (
    <div className="dashboard-layout-manager">
      {isEditing && (
        <div className="layout-edit-controls">
          <div className="layout-edit-message">
            <span>Editing Dashboard Layout</span>
            <p className="layout-edit-instructions">
              Drag and drop modules to rearrange them
            </p>
          </div>
          <div className="layout-edit-actions">
            <button className="layout-save-button" onClick={handleSaveLayout}>
              Save Layout
            </button>
            <button className="layout-cancel-button" onClick={handleCancelEdit}>
              Cancel
            </button>
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
          
          // If in edit mode, add drag and drop handlers
          const editProps = isEditing ? {
            draggable: true,
            onDragStart: (e) => handleDragStart(e, moduleId),
            onDragEnd: handleDragEnd,
            className: `module-wrapper ${isEditing ? 'editing' : ''} ${draggedItem === moduleId ? 'dragging' : ''}`,
          } : {};
          
          // Wrap the child in a div with the appropriate grid positioning
          return (
            <div 
              style={gridStyle}
              {...editProps}
            >
              {isEditing && <div className="module-drag-handle">⋮⋮</div>}
              {child}
            </div>
          );
        })}
        
        {/* If in edit mode, render drop zones */}
        {isEditing && (
          <div className="drop-zones-overlay">
            {Array.from({ length: 6 }).map((_, rowIndex) => (
              // Create drop zones at all positions to ensure small widgets can be placed anywhere
              [1, 4, 7, 10].map((colStart) => (
                <div 
                  key={`drop-${rowIndex}-${colStart}`}
                  className={`drop-zone ${colStart === 1 || colStart === 4 ? 'small-widget-zone' : ''}`}
                  onDragOver={(e) => handleDragOver(e, rowIndex + 1, colStart)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, rowIndex + 1, colStart)}
                  style={{
                    gridRow: rowIndex + 1,
                    gridColumn: colStart,
                    width: colStart === 1 || colStart === 4 ? '60px' : '40px' // Wider for small widget positions
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