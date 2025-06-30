import axios from 'axios';

// The base URL for our Core Engine API.
// Note: We use localhost:8000 because these requests are made from the user's
// browser, which is outside the Docker network. The docker-compose.yml file
// maps the host's port 8000 to the core service's port 8000.
const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// API version to use
const API_VERSION = 'v2';

// Create a pre-configured instance of axios
const apiClientV2 = axios.create({
  baseURL: BASE_URL,
});

// --- Axios Request Interceptor ---
// This is a powerful feature that intercepts every request sent by this client
// and allows us to modify it before it goes out.
apiClientV2.interceptors.request.use(
  (config) => {
    // Retrieve the auth token from local storage
    const token = localStorage.getItem('authToken');
    
    // If a token exists, add it to the Authorization header
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add API version header
    config.headers['X-API-Version'] = API_VERSION;
    
    return config;
  },
  (error) => {
    // Handle request error
    return Promise.reject(error);
  }
);

// --- Axios Response Interceptor ---
// This intercepts responses and handles authentication errors
apiClientV2.interceptors.response.use(
  (response) => {
    // Return successful responses as-is
    return response;
  },
  (error) => {
    // Handle 401 Unauthorized errors by clearing the token
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('authToken');
      // Reload the page to trigger the login flow
      window.location.reload();
    }
    
    // Handle API version deprecation warnings
    if (error.response && error.response.headers['x-api-deprecated'] === 'true') {
      console.warn(
        `API version ${API_VERSION} is deprecated and will be sunset on ${
          error.response.headers['x-api-sunset-date']
        }. Please upgrade to version ${
          error.response.headers['x-api-current-version']
        }.`
      );
    }
    
    return Promise.reject(error);
  }
);


// --- API Functions ---
// V2-specific API functions

export const getUILayout = () => {
  return apiClientV2.get('/api/v2/ui/layout');
};

export const getModuleState = (moduleName) => {
  return apiClientV2.get(`/api/v2/${moduleName}/state`);
};

export const updateModuleState = (moduleName, stateUpdate) => {
  return apiClientV2.post(`/api/v2/${moduleName}/state`, stateUpdate);
};

export const executeTool = (toolName, parameters = {}) => {
  return apiClientV2.post('/api/v2/execute', {
    tool_name: toolName,
    parameters
  });
};

export const getHealthCheck = () => {
  return apiClientV2.get('/api/v2/health');
};

export const getModules = () => {
  return apiClientV2.get('/api/v2/modules');
};

export const getApiVersions = () => {
  return apiClientV2.get('/api/versions');
};

export const getApiVersionInfo = (version) => {
  return apiClientV2.get(`/api/versions/${version}`);
};

export default apiClientV2;