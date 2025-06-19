import React from 'react';

const EmailPopout = ({ email, onClose }) => {
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

  return (
    <div className="email-popout-overlay" onClick={onClose}>
      <div className="email-popout-content" onClick={(e) => e.stopPropagation()}>
        <div className="email-popout-header">
          <h3>{email.subject || "(No Subject)"}</h3>
          <button className="email-popout-close" onClick={onClose}>×</button>
        </div>
        <div className="email-popout-body">
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
        </div>
      </div>
    </div>
  );
};

export default EmailPopout;