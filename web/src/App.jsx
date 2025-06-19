import React, { useState, createContext, useContext, useEffect } from 'react';
import { login as apiLogin } from './api/client';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import SettingsPage from './pages/SettingsPage';

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

    // Add event listener when dropdown is open
    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    // Clean up the event listener
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
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
    } else if (action === 'dashboard') {
      setCurrentPage('dashboard');
    }
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'settings':
        return <SettingsPage />;
      case 'dashboard':
      default:
        return <DashboardPage />;
    }
  };

  return (
    <div className="app-container">
      {isAuthenticated ? (
        <>
          <header className="app-header">
            <h1 onClick={() => handleMenuItemClick('dashboard')} style={{ cursor: 'pointer' }}>IntentVerse</h1>
            <div className="user-menu">
              <div ref={userIconRef} className="user-icon" onClick={toggleDropdown}>
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <circle cx="12" cy="10" r="3"></circle>
                  <path d="M12 13c-2.67 0-8 1.34-8 4v3h16v-3c0-2.66-5.33-4-8-4z"></path>
                </svg>
              </div>
              {dropdownOpen && (
                <div ref={dropdownRef} className="dropdown-menu">
                  <div className="dropdown-item" onClick={() => handleMenuItemClick('settings')}>Settings</div>
                  <div className="dropdown-item" onClick={() => handleMenuItemClick('logout')}>Logout</div>
                </div>
              )}
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
