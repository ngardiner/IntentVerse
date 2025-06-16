import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css'; 
import App from './App'; 

// Find the root DOM element from our index.html
const root = ReactDOM.createRoot(document.getElementById('root'));

// Render our main App component into the root element
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
