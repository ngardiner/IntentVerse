import React from 'react';
import ContentPackManager from '../components/ContentPackManager';

const ContentPage = () => {
  return (
    <div className="content-page-container">
      <h1>Content Management</h1>
      <div className="content-manager-wrapper">
        <ContentPackManager />
      </div>
    </div>
  );
};

export default ContentPage;