import React, { useState, useEffect } from 'react';
import { getUILayout } from '../api/client';

// We will create these generic components next.
// For now, we'll use placeholder divs.
const GenericFileTree = ({ title }) => <div className="module-placeholder"><h2>{title}</h2><p>(File Tree Component)</p></div>;
const GenericTable = ({ title }) => <div className="module-placeholder"><h2>{title}</h2><p>(Table Component)</p></div>;
const GenericKeyValue = ({ title }) => <div className="module-placeholder"><h2>{title}</h2><p>(Key-Value Component)</p></div>;


const DashboardPage = () => {
  const [layout, setLayout] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // useEffect hook to fetch data when the component mounts
  useEffect(() => {
    const fetchLayout = async () => {
      try {
        setLoading(true);
        const response = await getUILayout();
        setLayout(response.data.modules || []);
        setError(null);
      } catch (err) {
        setError("Failed to fetch UI layout from the server.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchLayout();
  }, []); // The empty dependency array ensures this runs only once on mount

  const renderComponent = (moduleSchema) => {
    // This function acts as a factory, returning the correct
    // generic component based on the schema from the backend.
    switch (moduleSchema.component_type) {
      case 'file_tree':
        return <GenericFileTree key={moduleSchema.module_id} {...moduleSchema} />;
      case 'table':
        return <GenericTable key={moduleSchema.module_id} {...moduleSchema} />;
      case 'key_value_viewer':
        return <GenericKeyValue key={moduleSchema.module_id} {...moduleSchema} />;
      default:
        return <div key={moduleSchema.module_id}>Unknown component type: {moduleSchema.component_type}</div>;
    }
  };

  if (loading) {
    return <div>Loading Dashboard...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  return (
    <div className="dashboard-container">
      <h1>IntentVerse Dashboard</h1>
      <div className="modules-grid">
        {layout.length > 0 ? (
          layout.map(renderComponent)
        ) : (
          <p>No modules loaded