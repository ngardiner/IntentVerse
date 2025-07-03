import axios from 'axios';
import {
  login,
  getCurrentUser,
  getModulesStatus,
  getModuleState,
  exportContentPack,
  getAvailableContentPacks,
  getLoadedContentPacks,
  getPackVariables,
  setPackVariable,
  resetPackVariable,
  resetAllPackVariables,
  previewContentPack
} from './client';

// Mock axios
jest.mock('axios');
const mockedAxios = axios;

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('login', () => {
    it('should make POST request to /auth/login with credentials', async () => {
      const mockResponse = { data: { access_token: 'test-token' } };
      mockedAxios.post.mockResolvedValue(mockResponse);

      const credentials = { username: 'admin', password: 'password' };
      const result = await login(credentials);

      // Expect URLSearchParams with form data and correct headers
      const expectedFormData = new URLSearchParams();
      expectedFormData.append('username', 'admin');
      expectedFormData.append('password', 'password');
      
      expect(mockedAxios.post).toHaveBeenCalledWith('/auth/login', expectedFormData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
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
    it('should make GET request to /users/me', async () => {
      const mockResponse = { data: { username: 'admin', id: 1 } };
      mockedAxios.get.mockResolvedValue(mockResponse);

      const result = await getCurrentUser();

      expect(mockedAxios.get).toHaveBeenCalledWith('/users/me');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getModulesStatus', () => {
    it('should make GET request to /api/v1/modules/status', async () => {
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

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/modules/status');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getModuleState', () => {
    it('should make GET request to /api/v1/{moduleName}/state', async () => {
      const mockResponse = { data: { files: [], directories: [] } };
      mockedAxios.get.mockResolvedValue(mockResponse);

      const result = await getModuleState('filesystem');

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/filesystem/state');
      expect(result).toEqual(mockResponse);
    });
  });


  describe('Content Pack API', () => {
    describe('getAvailableContentPacks', () => {
      it('should make GET request to /api/v1/content-packs/available', async () => {
        const mockResponse = { data: [{ id: 1, name: 'Test Pack' }] };
        mockedAxios.get.mockResolvedValue(mockResponse);

        const result = await getAvailableContentPacks();

        expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/content-packs/available');
        expect(result).toEqual(mockResponse);
      });
    });

    describe('getLoadedContentPacks', () => {
      it('should make GET request to /api/v1/content-packs/loaded', async () => {
        const mockResponse = { data: [{ id: 1, name: 'Loaded Pack' }] };
        mockedAxios.get.mockResolvedValue(mockResponse);

        const result = await getLoadedContentPacks();

        expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/content-packs/loaded');
        expect(result).toEqual(mockResponse);
      });
    });

    describe('exportContentPack', () => {
      it('should make POST request to /api/v1/content-packs/export with filename and metadata', async () => {
        const mockResponse = { data: { success: true } };
        mockedAxios.post.mockResolvedValue(mockResponse);

        const filename = 'test-pack.json';
        const metadata = { description: 'Test pack' };
        const result = await exportContentPack(filename, metadata);

        expect(mockedAxios.post).toHaveBeenCalledWith('/api/v1/content-packs/export', {
          filename,
          metadata
        });
        expect(result).toEqual(mockResponse);
      });
    });
  });

  describe('Variable Management API', () => {
    describe('getPackVariables', () => {
      it('should make GET request to /api/v1/content-packs/{packName}/variables', async () => {
        const mockResponse = { data: { variables: { test_var: 'test_value' } } };
        mockedAxios.get.mockResolvedValue(mockResponse);

        const result = await getPackVariables('Test Pack');

        expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/content-packs/Test%20Pack/variables');
        expect(result).toEqual(mockResponse);
      });

      it('should handle pack names with special characters', async () => {
        const mockResponse = { data: { variables: {} } };
        mockedAxios.get.mockResolvedValue(mockResponse);

        await getPackVariables('Test Pack & More!');

        expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/content-packs/Test%20Pack%20%26%20More!/variables');
      });
    });

    describe('setPackVariable', () => {
      it('should make PUT request to set a variable', async () => {
        const mockResponse = { data: { success: true } };
        mockedAxios.put.mockResolvedValue(mockResponse);

        const result = await setPackVariable('Test Pack', 'test_var', 'new_value');

        expect(mockedAxios.put).toHaveBeenCalledWith(
          '/api/v1/content-packs/Test%20Pack/variables/test_var',
          { value: 'new_value' }
        );
        expect(result).toEqual(mockResponse);
      });

      it('should handle empty values', async () => {
        const mockResponse = { data: { success: true } };
        mockedAxios.put.mockResolvedValue(mockResponse);

        await setPackVariable('Test Pack', 'test_var', '');

        expect(mockedAxios.put).toHaveBeenCalledWith(
          '/api/v1/content-packs/Test%20Pack/variables/test_var',
          { value: '' }
        );
      });

      it('should handle variable names with special characters', async () => {
        const mockResponse = { data: { success: true } };
        mockedAxios.put.mockResolvedValue(mockResponse);

        await setPackVariable('Test Pack', 'test_var_123', 'value');

        expect(mockedAxios.put).toHaveBeenCalledWith(
          '/api/v1/content-packs/Test%20Pack/variables/test_var_123',
          { value: 'value' }
        );
      });
    });

    describe('resetPackVariable', () => {
      it('should make DELETE request to reset a variable', async () => {
        const mockResponse = { data: { success: true } };
        mockedAxios.delete.mockResolvedValue(mockResponse);

        const result = await resetPackVariable('Test Pack', 'test_var');

        expect(mockedAxios.delete).toHaveBeenCalledWith(
          '/api/v1/content-packs/Test%20Pack/variables/test_var'
        );
        expect(result).toEqual(mockResponse);
      });
    });

    describe('resetAllPackVariables', () => {
      it('should make POST request to reset all variables', async () => {
        const mockResponse = { data: { success: true } };
        mockedAxios.post.mockResolvedValue(mockResponse);

        const result = await resetAllPackVariables('Test Pack');

        expect(mockedAxios.post).toHaveBeenCalledWith(
          '/api/v1/content-packs/Test%20Pack/variables/reset'
        );
        expect(result).toEqual(mockResponse);
      });
    });

    describe('previewContentPack', () => {
      it('should make GET request to preview content pack by filename', async () => {
        const mockResponse = { 
          data: { 
            content_pack: { 
              variables: { test_var: 'test_value' },
              content_prompts: [],
              usage_prompts: []
            } 
          } 
        };
        mockedAxios.get.mockResolvedValue(mockResponse);

        const result = await previewContentPack('test-pack.json');

        expect(mockedAxios.get).toHaveBeenCalledWith(
          '/api/v1/content-packs/preview/test-pack.json'
        );
        expect(result).toEqual(mockResponse);
      });
    });
  });
});