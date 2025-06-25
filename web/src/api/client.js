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

// --- Axios Response Interceptor ---
// This intercepts responses and handles authentication errors
apiClient.interceptors.response.use(
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
    
    return Promise.reject(error);
  }
);


// --- API Functions ---
// We export functions that our React components can use to talk to the API.

export const login = (credentials) => {
  const formData = new URLSearchParams();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);
  
  return apiClient.post('/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  });
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

// Timeline API Functions
export const getTimelineEvents = (filters = {}) => {
  return apiClient.get('/api/v1/timeline/events', { params: filters });
};

// --- User Management API Functions ---

export const getCurrentUser = () => {
  return apiClient.get('/users/me');
};

export const getUsers = (skip = 0, limit = 100) => {
  return apiClient.get(`/users/?skip=${skip}&limit=${limit}`);
};

export const getUser = (userId) => {
  return apiClient.get(`/users/${userId}`);
};

export const createUser = (userData) => {
  return apiClient.post('/users/', userData);
};

export const updateUser = (userId, userData) => {
  return apiClient.put(`/users/${userId}`, userData);
};

export const deleteUser = (userId) => {
  return apiClient.delete(`/users/${userId}`);
};

// --- Group Management API Functions ---

export const getGroups = (skip = 0, limit = 100) => {
  return apiClient.get(`/groups/?skip=${skip}&limit=${limit}`);
};

export const getGroup = (groupId) => {
  return apiClient.get(`/groups/${groupId}`);
};

export const createGroup = (groupData) => {
  return apiClient.post('/groups/', groupData);
};

export const updateGroup = (groupId, groupData) => {
  return apiClient.put(`/groups/${groupId}`, groupData);
};

export const deleteGroup = (groupId) => {
  return apiClient.delete(`/groups/${groupId}`);
};

export const addUserToGroup = (userId, groupId) => {
  return apiClient.post(`/users/${userId}/groups/${groupId}`);
};

export const removeUserFromGroup = (userId, groupId) => {
  return apiClient.delete(`/users/${userId}/groups/${groupId}`);
};

// --- Audit Log API Functions ---

export const getAuditLogs = (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.skip) queryParams.append('skip', params.skip);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.action) queryParams.append('action', params.action);
  if (params.username) queryParams.append('username', params.username);
  if (params.resource_type) queryParams.append('resource_type', params.resource_type);
  if (params.status) queryParams.append('status', params.status);
  if (params.start_date) queryParams.append('start_date', params.start_date);
  if (params.end_date) queryParams.append('end_date', params.end_date);
  
  return apiClient.get(`/audit-logs/?${queryParams.toString()}`);
};

export const getAuditLogStats = () => {
  return apiClient.get('/audit-logs/stats');
};

// --- Module Configuration API Functions ---

export const getModulesStatus = () => {
  return apiClient.get('/api/v1/modules/status');
};

export const toggleModule = (moduleName, enabled) => {
  return apiClient.post(`/api/v1/modules/${moduleName}/toggle`, { enabled });
};

export default apiClient;