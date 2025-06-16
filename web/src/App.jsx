import React, { useState, createContext, useContext, useEffect } from 'react';
import { login as apiLogin } from './api/client';
import DashboardPage from './pages/DashboardPage';

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
      setAuthToken(response.data.access_token);
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

// 4. Create a simple LoginPage component
const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login } = useAuth();

  const handleSubmit = (e) => {
    e.preventDefault();
    login({ username, password });
  };

  return (
    <div className="login-container">
      <form onSubmit={handleSubmit}>
        <h2>IntentVerse Login</h2>
        <div className="form-group">
          <label htmlFor="username">Username</label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit">Login</button>
      </form>
    </div>
  );
};


// 5. The Main App Component
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

// 6. Wrap the main App in the provider to make auth state available
const AppWrapper = () => (
  <AuthProvider>
    <App />
  </AuthProvider>
);

export default AppWrapper;
