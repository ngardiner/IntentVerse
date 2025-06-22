import React from 'react';

const EditButton = ({ isEditing, onClick }) => {
  return (
    <button 
      className={`edit-button ${isEditing ? 'active' : ''}`}
      onClick={onClick}
      title={isEditing ? "Exit edit mode" : "Edit dashboard layout"}
    >
      <svg 
        xmlns="http://www.w3.org/2000/svg" 
        width="18" 
        height="18" 
        viewBox="0 0 24 24" 
        fill="none" 
        stroke="currentColor" 
        strokeWidth="2" 
        strokeLinecap="round" 
        strokeLinejoin="round"
      >
        {isEditing ? (
          // X icon for cancel
          <>
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </>
        ) : (
          // Pencil icon for edit
          <>
            <path d="M12 20h9"></path>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
          </>
        )}
      </svg>
    </button>
  );
};

export default EditButton;