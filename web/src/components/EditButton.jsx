import React from 'react';

const EditButton = ({ isEditing, onClick }) => {
  return (
    <button 
      className={`edit-button ${isEditing ? 'active' : ''}`}
      onClick={onClick}
      title={isEditing ? "Exit edit mode" : "Edit dashboard layout"}
    >
      {isEditing ? (
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          width="18" 
          height="18" 
          viewBox="0 0 18 18"
        >
          <path 
            d="M 4 4 L 14 14 M 14 4 L 4 14"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      ) : (
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          width="18" 
          height="18" 
          viewBox="0 0 18 18" 
          fill="currentColor"
        >
          <path d="M 2 2 h 6 v 6 h -6 z M 10 2 h 6 v 6 h -6 z M 2 10 h 6 v 6 h -6 z M 10 10 h 6 v 6 h -6 z" />
        </svg>
      )}
    </button>
  );
};

export default EditButton;