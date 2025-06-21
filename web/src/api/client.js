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

export const loadContentPack = (filename) => {
  return apiClient.post('/api/v1/content-packs/load', {
    filename
  });
};

export const unloadContentPack = (identifier) => {
  return apiClient.post('/api/v1/content-packs/unload', {
    identifier
  });
};

export const clearAllLoadedPacks = () => {
  return apiClient.post('/api/v1/content-packs/clear-all');
};

export const previewContentPack = (filename) => {
  return apiClient.get(`/api/v1/content-packs/preview/${filename}`);
};

export const validateContentPack = (filename) => {
  return apiClient.post('/api/v1/content-packs/validate', {
    filename
  });
};

// Remote Content Pack API functions
export const getRemoteContentPacks = (forceRefresh = false) => {
  return apiClient.get(`/api/v1/content-packs/remote?force_refresh=${forceRefresh}`);
};

export const getRemoteContentPackInfo = (filename) => {
  return apiClient.get(`/api/v1/content-packs/remote/info/${filename}`);
};

export const searchRemoteContentPacks = (query = '', category = '', tags = []) => {
  return apiClient.post('/api/v1/content-packs/remote/search', {
    query,
    category,
    tags
  });
};

export const downloadRemoteContentPack = (filename) => {
  return apiClient.post('/api/v1/content-packs/remote/download', {
    filename
  });
};

export const installRemoteContentPack = (filename, loadImmediately = true) => {
  return apiClient.post('/api/v1/content-packs/remote/install', {
    filename,
    load_immediately: loadImmediately
  });
};

export const getRemoteRepositoryInfo = () => {
  return apiClient.get('/api/v1/content-packs/remote/repository-info');
};

export const refreshRemoteCache = () => {
  return apiClient.post('/api/v1/content-packs/remote/refresh-cache');
};

export const clearRemoteCache = () => {
  return apiClient.post('/api/v1/content-packs/remote/clear-cache');
};

// --- Filesystem API Functions ---

export const readFile = (path) => {
  return apiClient.post('/api/v1/execute', {
    tool_name: "filesystem.read_file",
    parameters: { path }
  });
};

export const writeFile = (path, content) => {
  return apiClient.post('/api/v1/execute', {
    tool_name: "filesystem.write_file",
    parameters: { path, content }
  });
};

export const deleteFile = (path) => {
  return apiClient.post('/api/v1/execute', {
    tool_name: "filesystem.delete_file",
    parameters: { path }
  });
};

export const createDirectory = (path) => {
  return apiClient.post('/api/v1/execute', {
    tool_name: "filesystem.create_directory",
    parameters: { path }
  });
};

export const deleteDirectory = (path) => {
  return apiClient.post('/api/v1/execute', {
    tool_name: "filesystem.delete_directory",
    parameters: { path }
  });
};

// Email API Functions
export const updateEmail = (emailId, updates) => {
  return apiClient.post('/api/v1/execute', {
    tool_name: "email.update_email",
    parameters: {
      email_id: emailId,
      ...updates
    }
  });
};

export default apiClient;