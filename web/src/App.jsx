import React, { useState, createContext, useContext, useEffect } from 'react';
import { login as apiLogin } from './api/client';
import DashboardPage from './pages/DashboardPage';
import TimelinePage from './pages/TimelinePage';
import LoginPage from './pages/LoginPage';
import SettingsPage from './pages/SettingsPage';
import ContentPage from './pages/ContentPage';
import DashboardSelector from './components/DashboardSelector';
import EditButton from './components/EditButton';

// 1. Create an Authentication Context
const AuthContext = createContext(null);

// 2. Create an AuthProvider Component
// This component will wrap our application and provide auth state to all children.
const AuthProvider = ({ children }) => {
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('authToken'));
  
  useEffect(() => {
    // Sync token changes to localStorage
    if (authToken) {
      localStorage.setItem('authToken', authToken);
    } else {
      localStorage.removeItem('authToken');
    }
  }, [authToken]);

  const login = async (credentials) => {
    try {
      const response = await apiLogin(credentials);
      if (response.data.access_token) {
        setAuthToken(response.data.access_token);
      }
    } catch (error) {
      console.error("Login failed:", error);
      // You might want to set an error state here to show in the UI
    }
  };

  const logout = () => {
    setAuthToken(null);
  };
  
  const value = {
    isAuthenticated: !!authToken,
    token: authToken,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// 3. Create a custom hook to easily access the auth context
export const useAuth = () => {
  return useContext(AuthContext);
};

// 4. The Main App Component
function App() {
  const { isAuthenticated, logout } = useAuth();
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [currentDashboard, setCurrentDashboard] = useState('state');
  const [isEditingLayout, setIsEditingLayout] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = React.useRef(null);
  const userIconRef = React.useRef(null);

  useEffect(() => {
    // Function to handle clicks outside the dropdown
    const handleClickOutside = (event) => {
      if (dropdownOpen && 
          dropdownRef.current && 
          !dropdownRef.current.contains(event.target) &&
          userIconRef.current &&
          !userIconRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };

    // Function to handle keyboard events
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && dropdownOpen) {
        setDropdownOpen(false);
      }
    };

    // Add event listeners when dropdown is open
    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }

    // Clean up the event listeners
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [dropdownOpen]);

  const toggleDropdown = () => {
    setDropdownOpen(!dropdownOpen);
  };

  const handleMenuItemClick = (action) => {
    setDropdownOpen(false);
    
    if (action === 'logout') {
      logout();
    } else if (action === 'settings') {
      setCurrentPage('settings');
      setIsEditingLayout(false);
    } else if (action === 'content') {
      setCurrentPage('content');
      setIsEditingLayout(false);
    } else if (action === 'dashboard') {
      setCurrentPage('dashboard');
    }
  };

  const handleDashboardChange = (dashboardId) => {
    setCurrentDashboard(dashboardId);
    // Exit edit mode when changing dashboards
    if (isEditingLayout) {
      setIsEditingLayout(false);
    }
  };
  
  const toggleEditMode = () => {
    setIsEditingLayout(!isEditingLayout);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'settings':
        return <SettingsPage />;
      case 'content':
        return <ContentPage />;
      case 'dashboard':
      default:
        // Render different dashboards based on currentDashboard state
        return currentDashboard === 'state' ? (
          <DashboardPage 
            isEditing={isEditingLayout} 
            onSaveLayout={() => setIsEditingLayout(false)} 
            onCancelEdit={() => setIsEditingLayout(false)}
            currentDashboard={currentDashboard}
          />
        ) : (
          <TimelinePage 
            isEditing={isEditingLayout} 
            onSaveLayout={() => setIsEditingLayout(false)} 
            onCancelEdit={() => setIsEditingLayout(false)}
            currentDashboard={currentDashboard}
          />
        );
    }
  };

  return (
    <div className="app-container">
      {isAuthenticated ? (
        <>
          <header className="app-header">
            <div className="app-header-left">
              <h1 onClick={() => handleMenuItemClick('dashboard')} style={{ cursor: 'pointer' }}>IntentVerse</h1>
              {currentPage === 'dashboard' && (
                <DashboardSelector 
                  currentDashboard={currentDashboard} 
                  onDashboardChange={handleDashboardChange} 
                />
              )}
            </div>
            <div className="app-header-right">
              {currentPage === 'dashboard' && (
                <EditButton 
                  isEditing={isEditingLayout}
                  onClick={toggleEditMode}
                />
              )}
              <div className="user-menu">
                <div ref={userIconRef} className="user-icon" onClick={toggleDropdown}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <circle cx="12" cy="10" r="3"></circle>
                    <path d="M12 13c-2.67 0-8 1.34-8 4v3h16v-3c0-2.66-5.33-4-8-4z"></path>
                  </svg>
                </div>
                <div 
                  ref={dropdownRef} 
                  className={`dropdown-menu ${dropdownOpen ? 'dropdown-menu-visible' : ''}`}
                >
                  <div className="dropdown-item" onClick={() => handleMenuItemClick('content')}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="menu-icon">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                      <polyline points="14 2 14 8 20 8"></polyline>
                      <line x1="16" y1="13" x2="8" y2="13"></line>
                      <line x1="16" y1="17" x2="8" y2="17"></line>
                      <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                    <span>Content</span>
                  </div>
                  <div className="dropdown-item" onClick={() => handleMenuItemClick('settings')}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="menu-icon">
                      <circle cx="12" cy="12" r="3"></circle>
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                    </svg>
                    <span>Settings</span>
                  </div>
                  <div className="dropdown-divider"></div>
                  <div className="dropdown-item" onClick={() => handleMenuItemClick('logout')}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="menu-icon">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                      <polyline points="16 17 21 12 16 7"></polyline>
                      <line x1="21" y1="12" x2="9" y2="12"></line>
                    </svg>
                    <span>Logout</span>
                  </div>
                </div>
              </div>
            </div>
          </header>
          {renderPage()}
        </>
      ) : (
        <LoginPage />
      )}
    </div>
  );
}

// 5. Export a single wrapped component
// This ensures that our App is always wrapped with the AuthProvider.
const AppWrapper = () => (
  <AuthProvider>
    <App />
  </AuthProvider>
);

export default AppWrapper;