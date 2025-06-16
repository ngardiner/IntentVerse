import React, { useState, createContext, useContext, useEffect } from 'react';
import { login as apiLogin } from './api/client';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';

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

  return (
    <div className="app-container">
      {isAuthenticated ? (
        <>
          <header className="app-header">
            <h1>IntentVerse</h1>
            <button onClick={logout}>Logout</button>
          </header>
          <DashboardPage />
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
