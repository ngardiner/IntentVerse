import React, { useState } from 'react';
import { executeQuery } from '../../api/client';

const QueryExecutor = ({ 
  title,
  description,
  module_id,
  onQueryExecuted
}) => {
  const [query, setQuery] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState(null);

  const handleClear = () => {
    setQuery('');
    setError(null);
  };

  const handleExecuteQuery = async () => {
    if (!query.trim()) {
      setError('Please enter a query to execute');
      return;
    }

    setIsExecuting(true);
    setError(null);

    try {
      const response = await executeQuery(query.trim());
      
      if (response.data.status === 'success') {
        // Clear the query after successful execution
        setQuery('');
        
        // Notify parent component that query was executed successfully
        // This will trigger switching to the Last Query Result view
        if (onQueryExecuted) {
          onQueryExecuted();
        }
      } else {
        setError('Query execution failed');
      }
    } catch (err) {
      console.error('Error executing query:', err);
      setError(err.response?.data?.detail || 'Failed to execute query. Please check your query syntax.');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleKeyDown = (e) => {
    // Allow Ctrl+Enter or Cmd+Enter to execute query
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleExecuteQuery();
    }
  };

  return (
    <div className="query-executor">
      {title && <h3 className="query-executor-title">{title}</h3>}
      {description && <p className="query-executor-description">{description}</p>}
      
      <div className="query-executor-content">
        <div className="query-input-container">
          <textarea
            className="query-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter your SQL query here... (Ctrl+Enter to execute)"
            rows={6}
            disabled={isExecuting}
          />
        </div>
        
        <div className="query-executor-actions">
          <button
            className="btn btn-secondary"
            onClick={handleClear}
            disabled={isExecuting || !query.trim()}
          >
            Clear
          </button>
          <button
            className="btn btn-primary"
            onClick={handleExecuteQuery}
            disabled={isExecuting || !query.trim()}
          >
            {isExecuting ? 'Executing...' : 'Execute Query'}
          </button>
        </div>
        
        {error && (
          <div className="error-message query-executor-error">
            {error}
          </div>
        )}
        
        <div className="query-executor-hint">
          <small>
            Tip: Use Ctrl+Enter (Cmd+Enter on Mac) to quickly execute your query
          </small>
        </div>
      </div>
    </div>
  );
};

export default QueryExecutor;