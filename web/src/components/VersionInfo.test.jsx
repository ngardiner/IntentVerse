import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import VersionInfo from './VersionInfo';
import * as apiClient from '../api/client';

// Mock the API client
jest.mock('../api/client');

describe('VersionInfo', () => {
  const mockVersionInfo = {
    version: '1.0.0',
    major: 1,
    minor: 0,
    patch: 0,
    semantic_version: true
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders version info correctly', async () => {
    apiClient.getVersionInfo.mockResolvedValue(mockVersionInfo);

    render(<VersionInfo />);

    await waitFor(() => {
      expect(screen.getByText('IntentVerse')).toBeInTheDocument();
      expect(screen.getByText('v1.0.0')).toBeInTheDocument();
      expect(screen.getByText('SemVer')).toBeInTheDocument();
    });
  });

  test('renders inline version correctly', async () => {
    apiClient.getVersionInfo.mockResolvedValue(mockVersionInfo);

    render(<VersionInfo inline={true} />);

    await waitFor(() => {
      expect(screen.getByText('IntentVerse v1.0.0')).toBeInTheDocument();
    });
  });

  test('shows details when showDetails is true', async () => {
    apiClient.getVersionInfo.mockResolvedValue(mockVersionInfo);

    render(<VersionInfo showDetails={true} />);

    await waitFor(() => {
      expect(screen.getByText('Major:')).toBeInTheDocument();
      expect(screen.getByText('Minor:')).toBeInTheDocument();
      expect(screen.getByText('Patch:')).toBeInTheDocument();
      
      // Use function-based text matcher to handle text broken up by multiple elements
      expect(screen.getByText((content, element) => {
        return element && element.textContent === 'Major: 1';
      })).toBeInTheDocument();
      
      expect(screen.getByText((content, element) => {
        return element && element.textContent === 'Minor: 0';
      })).toBeInTheDocument();
      
      expect(screen.getByText((content, element) => {
        return element && element.textContent === 'Patch: 0';
      })).toBeInTheDocument();
    });
  });

  test('shows loading state initially', () => {
    apiClient.getVersionInfo.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({}), 100))); // Resolves after 100ms

    render(<VersionInfo />);

    expect(screen.getByText('Loading version...')).toBeInTheDocument();
  });

  test('shows error state when API call fails', async () => {
    apiClient.getVersionInfo.mockRejectedValue(new Error('API Error'));

    render(<VersionInfo />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load version information/)).toBeInTheDocument();
    });
  });

  test('applies custom className', async () => {
    apiClient.getVersionInfo.mockResolvedValue(mockVersionInfo);

    const { container } = render(<VersionInfo className="custom-class" />);

    await waitFor(() => {
      expect(container.firstChild).toHaveClass('custom-class');
    });
  });

  test('renders nothing when version info is null', async () => {
    apiClient.getVersionInfo.mockResolvedValue(null);

    const { container } = render(<VersionInfo />);

    await waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });
});