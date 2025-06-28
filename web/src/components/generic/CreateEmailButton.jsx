import React from 'react';
import { createDraft, getModuleState } from '../../api/client';

const CreateEmailButton = ({ onEmailCreated }) => {
  const handleCreateEmail = async () => {
    try {
      // Create a new draft email
      const response = await createDraft([], '', '');
      
      if (response.data && response.data.email_id) {
        // Create a new email object for the popout
        const newEmail = {
          email_id: response.data.email_id,
          to: [],
          cc: [],
          subject: '',
          body: '',
          timestamp: new Date().toISOString(),
          isNewDraft: true // Flag to indicate this is a new draft
        };
        
        // Call the callback to handle the new email
        if (onEmailCreated) {
          onEmailCreated(newEmail);
        }
      }
    } catch (error) {
      console.error('Failed to create new email draft:', error);
      // You could add a toast notification here
    }
  };

  return (
    <button 
      className="create-email-button" 
      onClick={handleCreateEmail}
      aria-label="Create new email"
      title="Create new email"
    >
      <span className="create-email-icon">+</span>
    </button>
  );
};

export default CreateEmailButton;