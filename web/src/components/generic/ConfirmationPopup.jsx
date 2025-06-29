import React from 'react';

const ConfirmationPopup = ({ message, onConfirm, onCancel, status }) => {
  const isProcessing = status === 'deleting';
  const isSuccess = status === 'success';
  const isError = status === 'error';
  const showButtons = !isProcessing && !isSuccess && !isError;

  return (
    <div className="confirmation-popup-overlay" onClick={showButtons ? onCancel : null}>
      <div className="confirmation-popup-content" onClick={(e) => e.stopPropagation()}>
        <div className="confirmation-popup-header">
          <h3>
            {isSuccess ? 'Success' : isError ? 'Error' : 'Confirmation'}
          </h3>
          {showButtons && (
            <button className="confirmation-popup-close" onClick={onCancel}>×</button>
          )}
        </div>
        <div className="confirmation-popup-body">
          <p className={`confirmation-message ${status || ''}`}>{message}</p>
        </div>
        {showButtons && (
          <div className="confirmation-popup-footer">
            <button 
              className="confirmation-popup-cancel" 
              onClick={onCancel}
              disabled={isProcessing}
            >
              Cancel
            </button>
            <button 
              className="confirmation-popup-confirm" 
              onClick={onConfirm}
              disabled={isProcessing || isSuccess || isError}
            >
              Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConfirmationPopup;