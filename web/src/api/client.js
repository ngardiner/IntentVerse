// web/src/api/client.js

import axios from 'axios';

// The base URL for our Core Engine API.
// Note: We use localhost:8000 because these requests are made from the user's
// browser, which is outside the Docker network. The docker-compose.yml file
// maps the host's port 8000 to the core service's port 8000.
const BASE_URL = 'http://localhost:8000';

// Create a pre-configured instance of axios
const apiClient = axios.create({
  baseURL: BASE_URL,
});

// --- Axios Request Interceptor ---
// This is a powerful feature that intercepts every request sent by this client
// and allows us to modify it before it goes out.
apiClient.interceptors.request.use(
  (config) => {
    // Retrieve the auth token from local storage
    const token = localStorage.getItem('authToken');
    
    // If a token exists, add it to the Authorization header
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    // Handle request error
    return Promise.reject(error);
  }
);


// --- API Functions ---
// We export functions that our React components can use to talk to the API.

export const login = (credentials) => {
  // This is a placeholder for the auth endpoint we'll build
  // return apiClient.post('/auth/login', credentials);
  console.log("Logging in with:", credentials);
  // For now, let's just return a fake token for testing
  return Promise.resolve({ data: { access_token: "fake-jwt-token" } });
};

export const getUILayout = () => {
  return apiClient.get('/api/v1/ui/layout');
};

export const getModuleState = (moduleName) => {
  return apiClient.get(`/api/v1/${moduleName}/state`);
};

// --- Content Pack API Functions ---

export const getAvailableContentPacks = () => {
  return apiClient.get('/api/v1/content-packs/available');
};

export const getLoadedContentPacks = () => {
  return apiClient.get('/api/v1/content-packs/loaded');
};

export const exportContentPack = (filename, metadata = {}) => {
  return apiClient.post('/api/v1/content-packs/export', {
    filename,
    metadata
  });
};

export default apiClient;