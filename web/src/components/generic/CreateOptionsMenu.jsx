import React, { useRef, useEffect } from 'react';

const CreateOptionsMenu = ({ onCreateFile, onCreateDirectory, onClose, position }) => {
  const menuRef = useRef(null);
  
  useEffect(() => {
    // Close the menu when clicking outside
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        onClose();
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  const handleCreateFile = (e) => {
    e.stopPropagation();
    onCreateFile();
    onClose();
  };

  const handleCreateDirectory = (e) => {
    e.stopPropagation();
    onCreateDirectory();
    onClose();
  };

  const style = {
    top: `${position.y}px`,
    left: `${position.x}px`,
  };

  return (
    <div className="create-options-menu" style={style} ref={menuRef}>
      <div className="create-options-menu-item" onClick={handleCreateFile}>
        <span className="create-options-icon">📄</span>
        <span>New File</span>
      </div>
      <div className="create-options-menu-item" onClick={handleCreateDirectory}>
        <span className="create-options-icon">📁</span>
        <span>New Directory</span>
      </div>
    </div>
  );
};

export default CreateOptionsMenu;