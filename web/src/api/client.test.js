import axios from 'axios';
import {
  login,
  getCurrentUser,
  getModulesStatus,
  getModuleState,
  setModuleState,
  getContentPacks,
  importContentPack,
  exportContentPack,
  deleteContentPack
} from './client';

// Mock axios
jest.mock('axios');
const mockedAxios = axios;

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset axios defaults
    delete axios.defaults.headers.common['Authorization'];
  });

  describe('login', () => {
    it('should make POST request to /auth/login with credentials', async () => {
      const mockResponse = { data: { access_token: 'test-token' } };
      mockedAxios.post.mockResolvedValue(mockResponse);

      const credentials = { username: 'admin', password: 'password' };
      const result = await login(credentials);

      expect(mockedAxios.post).toHaveBeenCalledWith('/auth/login', credentials);
      expect(result).toEqual(mockResponse);
    });

    it('should handle login errors', async () => {
      const mockError = new Error('Login failed');
      mockedAxios.post.mockRejectedValue(mockError);

      const credentials = { username: 'admin', password: 'wrong' };
      
      await expect(login(credentials)).rejects.toThrow('Login failed');
    });
  });

  describe('getCurrentUser', () => {
    it('should make GET request to /auth/me with authorization header', async () => {
      const mockResponse = { data: { username: 'admin', id: 1 } };
      mockedAxios.get.mockResolvedValue(mockResponse);

      const token = 'test-token';
      const result = await getCurrentUser(token);

      expect(mockedAxios.get).toHaveBeenCalledWith('/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getModulesStatus', () => {
    it('should make GET request to /modules/status', async () => {
      const mockResponse = { 
        data: { 
          modules: { 
            filesystem: { is_enabled: true, is_loaded: true },
            email: { is_enabled: true, is_loaded: true }
          } 
        } 
      };
      mockedAxios.get.mockResolvedValue(mockResponse);

      const result = await getModulesStatus();

      expect(mockedAxios.get).toHaveBeenCalledWith('/modules/status');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getModuleState', () => {
    it('should make GET request to /modules/{moduleName}/state', async () => {
      const mockResponse = { data: { files: [], directories: [] } };
      mockedAxios.get.mockResolvedValue(mockResponse);

      const result = await getModuleState('filesystem');

      expect(mockedAxios.get).toHaveBeenCalledWith('/modules/filesystem/state');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('setModuleState', () => {
    it('should make PUT request to /modules/{moduleName}/state with new state', async () => {
      const mockResponse = { data: { success: true } };
      mockedAxios.put.mockResolvedValue(mockResponse);

      const newState = { files: ['test.txt'], directories: ['docs'] };
      const result = await setModuleState('filesystem', newState);

      expect(mockedAxios.put).toHaveBeenCalledWith('/modules/filesystem/state', newState);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Content Pack API', () => {
    describe('getContentPacks', () => {
      it('should make GET request to /content-packs', async () => {
        const mockResponse = { data: [{ id: 1, name: 'Test Pack' }] };
        mockedAxios.get.mockResolvedValue(mockResponse);

        const result = await getContentPacks();

        expect(mockedAxios.get).toHaveBeenCalledWith('/content-packs');
        expect(result).toEqual(mockResponse);
      });
    });

    describe('importContentPack', () => {
      it('should make POST request to /content-packs/import with pack data', async () => {
        const mockResponse = { data: { success: true, id: 1 } };
        mockedAxios.post.mockResolvedValue(mockResponse);

        const packData = { name: 'Test Pack', modules: {} };
        const result = await importContentPack(packData);

        expect(mockedAxios.post).toHaveBeenCalledWith('/content-packs/import', packData);
        expect(result).toEqual(mockResponse);
      });
    });

    describe('exportContentPack', () => {
      it('should make GET request to /content-packs/{packId}/export', async () => {
        const mockResponse = { data: { name: 'Test Pack', modules: {} } };
        mockedAxios.get.mockResolvedValue(mockResponse);

        const result = await exportContentPack(1);

        expect(mockedAxios.get).toHaveBeenCalledWith('/content-packs/1/export');
        expect(result).toEqual(mockResponse);
      });
    });

    describe('deleteContentPack', () => {
      it('should make DELETE request to /content-packs/{packId}', async () => {
        const mockResponse = { data: { success: true } };
        mockedAxios.delete.mockResolvedValue(mockResponse);

        const result = await deleteContentPack(1);

        expect(mockedAxios.delete).toHaveBeenCalledWith('/content-packs/1');
        expect(result).toEqual(mockResponse);
      });
    });
  });
});