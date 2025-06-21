import React, { useState } from 'react';
import { updateEmail } from '../../api/client';

const EmailPopout = ({ email, onClose }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedEmail, setEditedEmail] = useState(email ? { ...email } : null);
  const [saveStatus, setSaveStatus] = useState(null);
  const [error, setError] = useState(null);

  if (!email) return null;
  
  // Format date safely
  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr);
      return !isNaN(date.getTime()) ? date.toLocaleString() : "Unknown Date";
    } catch (e) {
      return "Unknown Date";
    }
  };
  
  // Format recipients safely
  const formatRecipients = (recipients) => {
    if (!recipients) return "None";
    if (Array.isArray(recipients)) {
      return recipients.length > 0 ? recipients.join(", ") : "None";
    }
    return recipients;
  };

  // Parse recipients string into array
  const parseRecipients = (recipientsStr) => {
    if (!recipientsStr || recipientsStr === "None") return [];
    return recipientsStr.split(',').map(email => email.trim()).filter(email => email);
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditedEmail({ ...email });
    setSaveStatus(null);
    setError(null);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setSaveStatus(null);
    setError(null);
  };

  const handleSave = async () => {
    try {
      setSaveStatus('saving');
      
      // Prepare the update data
      const updates = {
        from_address: editedEmail.from,
        to: parseRecipients(editedEmail.to),
        cc: parseRecipients(editedEmail.cc),
        subject: editedEmail.subject,
        body: editedEmail.body
      };
      
      const response = await updateEmail(email.email_id, updates);
      
      if (response.data.status === 'success') {
        setSaveStatus('success');
        // Update the original email object with the edited values
        Object.assign(email, editedEmail);
        setTimeout(() => {
          setSaveStatus(null);
          setIsEditing(false);
        }, 1500);
      } else {
        throw new Error('Failed to update email');
      }
    } catch (err) {
      setSaveStatus('error');
      setError(`Failed to save email: ${err.message}`);
      console.error(err);
    }
  };

  const handleInputChange = (field, value) => {
    setEditedEmail(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <div className="email-popout-overlay" onClick={onClose}>
      <div className="email-popout-content" onClick={(e) => e.stopPropagation()}>
        <div className="email-popout-header">
          <h3>{isEditing ? "Edit Email" : (email.subject || "(No Subject)")}</h3>
          <div className="email-popout-actions">
            {!isEditing && (
              <button 
                className="email-popout-edit" 
                onClick={handleEdit}
              >
                Edit
              </button>
            )}
            {isEditing && (
              <>
                <button 
                  className="email-popout-save" 
                  onClick={handleSave}
                  disabled={saveStatus === 'saving'}
                >
                  Save
                </button>
                <button 
                  className="email-popout-cancel" 
                  onClick={handleCancel}
                  disabled={saveStatus === 'saving'}
                >
                  Cancel
                </button>
              </>
            )}
            <button className="email-popout-close" onClick={onClose}>×</button>
          </div>
        </div>
        <div className="email-popout-body">
          {isEditing ? (
            <div className="email-edit-form">
              <div className="email-form-group">
                <label>From:</label>
                <input
                  type="text"
                  value={editedEmail.from || ''}
                  onChange={(e) => handleInputChange('from', e.target.value)}
                  className="email-form-input"
                />
              </div>
              <div className="email-form-group">
                <label>To:</label>
                <input
                  type="text"
                  value={Array.isArray(editedEmail.to) ? editedEmail.to.join(', ') : editedEmail.to || ''}
                  onChange={(e) => handleInputChange('to', e.target.value)}
                  className="email-form-input"
                  placeholder="Separate multiple emails with commas"
                />
              </div>
              <div className="email-form-group">
                <label>CC:</label>
                <input
                  type="text"
                  value={Array.isArray(editedEmail.cc) ? editedEmail.cc.join(', ') : editedEmail.cc || ''}
                  onChange={(e) => handleInputChange('cc', e.target.value)}
                  className="email-form-input"
                  placeholder="Separate multiple emails with commas"
                />
              </div>
              <div className="email-form-group">
                <label>Subject:</label>
                <input
                  type="text"
                  value={editedEmail.subject || ''}
                  onChange={(e) => handleInputChange('subject', e.target.value)}
                  className="email-form-input"
                />
              </div>
              <div className="email-form-group">
                <label>Body:</label>
                <textarea
                  value={editedEmail.body || ''}
                  onChange={(e) => handleInputChange('body', e.target.value)}
                  className="email-form-textarea"
                  rows={10}
                />
              </div>
              {error && <div className="email-error">{error}</div>}
              {saveStatus === 'saving' && <div className="email-status saving">Saving changes...</div>}
              {saveStatus === 'success' && <div className="email-status success">Email updated successfully!</div>}
            </div>
          ) : (
            <>
              <div className="email-popout-metadata">
                <div className="email-meta-item">
                  <span className="email-meta-label">From:</span>
                  <span className="email-meta-value">{email.from || "unknown@example.com"}</span>
                </div>
                <div className="email-meta-item">
                  <span className="email-meta-label">To:</span>
                  <span className="email-meta-value">{formatRecipients(email.to)}</span>
                </div>
                {email.cc && email.cc.length > 0 && (
                  <div className="email-meta-item">
                    <span className="email-meta-label">CC:</span>
                    <span className="email-meta-value">{formatRecipients(email.cc)}</span>
                  </div>
                )}
                <div className="email-meta-item">
                  <span className="email-meta-label">Date:</span>
                  <span className="email-meta-value">{formatDate(email.timestamp)}</span>
                </div>
              </div>
              <div className="email-popout-content-body">
                <p style={{ whiteSpace: 'pre-wrap' }}>{email.body || "(No content)"}</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmailPopout;