import React from 'react';

const EmailPopout = ({ email, onClose }) => {
  if (!email) return null;

  return (
    <div className="email-popout-overlay" onClick={onClose}>
      <div className="email-popout-content" onClick={(e) => e.stopPropagation()}>
        <div className="email-popout-header">
          <h3>{email.subject}</h3>
          <button className="email-popout-close" onClick={onClose}>×</button>
        </div>
        <div className="email-popout-body">
          <div className="email-popout-metadata">
            <div className="email-meta-item">
              <span className="email-meta-label">From:</span>
              <span className="email-meta-value">{email.from}</span>
            </div>
            <div className="email-meta-item">
              <span className="email-meta-label">To:</span>
              <span className="email-meta-value">{email.to}</span>
            </div>
            {email.cc && (
              <div className="email-meta-item">
                <span className="email-meta-label">CC:</span>
                <span className="email-meta-value">{email.cc}</span>
              </div>
            )}
            <div className="email-meta-item">
              <span className="email-meta-label">Date:</span>
              <span className="email-meta-value">{new Date(email.date).toLocaleString()}</span>
            </div>
          </div>
          <div className="email-popout-content-body">
            <p>{email.body}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmailPopout;