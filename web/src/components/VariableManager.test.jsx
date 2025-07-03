import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import VariableManager from './VariableManager';
import * as apiClient from '../api/client';

// Mock the API client
jest.mock('../api/client');

describe('VariableManager', () => {
  const mockProps = {
    packName: 'Test Pack',
    packFilename: 'test-pack.json',
    isOpen: true,
    onClose: jest.fn(),
  };

  const mockPackDefaults = {
    company_name: 'Default Corp',
    email_domain: 'default.com',
    support_email: 'support@{{email_domain}}',
  };

  const mockUserVariables = {
    company_name: 'Custom Corp',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock API responses
    apiClient.getPackVariables.mockResolvedValue({
      data: { variables: mockUserVariables }
    });
    
    apiClient.previewContentPack.mockResolvedValue({
      data: { 
        content_pack: { 
          variables: mockPackDefaults 
        }
      }
    });
    
    apiClient.setPackVariable.mockResolvedValue({});
    apiClient.resetPackVariable.mockResolvedValue({});
    apiClient.resetAllPackVariables.mockResolvedValue({});
  });

  describe('Component Rendering', () => {
    it('should not render when isOpen is false', () => {
      render(<VariableManager {...mockProps} isOpen={false} />);
      expect(screen.queryByText('Variable Manager: Test Pack')).not.toBeInTheDocument();
    });

    it('should render when isOpen is true', () => {
      render(<VariableManager {...mockProps} />);
      expect(screen.getByText('Manage Variables: Test Pack')).toBeInTheDocument();
    });

    it('should show loading state initially', () => {
      render(<VariableManager {...mockProps} />);
      expect(screen.getByText('Loading variables...')).toBeInTheDocument();
    });

    it('should call onClose when close button is clicked', () => {
      render(<VariableManager {...mockProps} />);
      
      const closeButton = screen.getByText('×');
      fireEvent.click(closeButton);
      
      expect(mockProps.onClose).toHaveBeenCalled();
    });

    it('should call onClose when overlay is clicked', () => {
      render(<VariableManager {...mockProps} />);
      
      const overlay = screen.getByRole('dialog').parentElement;
      fireEvent.click(overlay);
      
      expect(mockProps.onClose).toHaveBeenCalled();
    });

    it('should not call onClose when modal content is clicked', () => {
      render(<VariableManager {...mockProps} />);
      
      const modalContent = screen.getByRole('dialog');
      fireEvent.click(modalContent);
      
      expect(mockProps.onClose).not.toHaveBeenCalled();
    });
  });

  describe('Data Loading', () => {
    it('should load pack data when component opens', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        expect(apiClient.getPackVariables).toHaveBeenCalledWith('Test Pack');
        expect(apiClient.previewContentPack).toHaveBeenCalledWith('test-pack.json');
      });
    });

    it('should not load data when packName or packFilename is missing', () => {
      render(<VariableManager {...mockProps} packName="" />);
      
      expect(apiClient.getPackVariables).not.toHaveBeenCalled();
      expect(apiClient.previewContentPack).not.toHaveBeenCalled();
    });

    it('should handle API errors gracefully', async () => {
      apiClient.getPackVariables.mockRejectedValue(new Error('API Error'));
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });

    it('should retry loading on retry button click', async () => {
      apiClient.getPackVariables.mockRejectedValueOnce(new Error('API Error'));
      apiClient.getPackVariables.mockResolvedValueOnce({
        data: { variables: mockUserVariables }
      });
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('Retry'));
      
      await waitFor(() => {
        expect(apiClient.getPackVariables).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Variable Display', () => {
    it('should display message when no variables are defined', async () => {
      apiClient.previewContentPack.mockResolvedValue({
        data: { content_pack: { variables: {} } }
      });
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('This content pack does not define any variables.')).toBeInTheDocument();
      });
    });

    it('should display all variables from pack defaults', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('{{company_name}}')).toBeInTheDocument();
        expect(screen.getByText('{{email_domain}}')).toBeInTheDocument();
        expect(screen.getByText('{{support_email}}')).toBeInTheDocument();
      });
    });

    it('should show customized badge for user overrides', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        // company_name has a user override
        const companyNameRow = screen.getByText('{{company_name}}').closest('.variable-row');
        expect(companyNameRow).toHaveTextContent('Custom');
        
        // email_domain does not have a user override
        const emailDomainRow = screen.getByText('{{email_domain}}').closest('.variable-row');
        expect(emailDomainRow).not.toHaveTextContent('Custom');
      });
    });

    it('should display current and default values correctly', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        // For customized variable, should show both current and default
        expect(screen.getByText('Custom Corp')).toBeInTheDocument(); // Current value
        expect(screen.getByText('Default Corp')).toBeInTheDocument(); // Default value
        
        // For non-customized variable, should show only current (which is default)
        expect(screen.getByText('default.com')).toBeInTheDocument();
      });
    });

    it('should show variable statistics', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('3')).toBeInTheDocument(); // total variables
        expect(screen.getByText('1')).toBeInTheDocument(); // customized variables
      });
    });
  });

  describe('Variable Editing', () => {
    it('should enter edit mode when edit button is clicked', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const editButton = screen.getAllByText('Edit')[0];
        fireEvent.click(editButton);
        
        expect(screen.getByDisplayValue('Custom Corp')).toBeInTheDocument();
        expect(screen.getByText('Save')).toBeInTheDocument();
        expect(screen.getByText('Cancel')).toBeInTheDocument();
      });
    });

    it('should cancel edit mode when cancel button is clicked', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const editButton = screen.getAllByText('Edit')[0];
        fireEvent.click(editButton);
        
        const cancelButton = screen.getByText('Cancel');
        fireEvent.click(cancelButton);
        
        expect(screen.queryByDisplayValue('Custom Corp')).not.toBeInTheDocument();
        expect(screen.queryByText('Save')).not.toBeInTheDocument();
      });
    });

    it('should update input value when typing', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const editButton = screen.getAllByText('Edit')[0];
        fireEvent.click(editButton);
        
        const input = screen.getByDisplayValue('Custom Corp');
        fireEvent.change(input, { target: { value: 'New Corp Name' } });
        
        expect(screen.getByDisplayValue('New Corp Name')).toBeInTheDocument();
      });
    });

    it('should save variable when save button is clicked', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const editButton = screen.getAllByText('Edit')[0];
        fireEvent.click(editButton);
        
        const input = screen.getByDisplayValue('Custom Corp');
        fireEvent.change(input, { target: { value: 'New Corp Name' } });
        
        const saveButton = screen.getByText('Save');
        fireEvent.click(saveButton);
      });
      
      await waitFor(() => {
        expect(apiClient.setPackVariable).toHaveBeenCalledWith(
          'Test Pack',
          'company_name',
          'New Corp Name'
        );
      });
    });

    it('should disable save button when input is empty', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const editButton = screen.getAllByText('Edit')[0];
        fireEvent.click(editButton);
        
        const input = screen.getByDisplayValue('Custom Corp');
        fireEvent.change(input, { target: { value: '' } });
        
        const saveButton = screen.getByText('Save');
        expect(saveButton).toBeDisabled();
      });
    });

    it('should show default value reference during editing', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const editButton = screen.getAllByText('Edit')[0];
        fireEvent.click(editButton);
        
        expect(screen.getByText('Default:')).toBeInTheDocument();
        expect(screen.getByText('Default Corp')).toBeInTheDocument();
      });
    });
  });

  describe('Variable Reset', () => {
    it('should show reset button only for customized variables', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const variableRows = screen.getAllByText(/\{\{.*\}\}/).map(el => el.closest('.variable-row'));
        
        // company_name (customized) should have reset button
        const companyNameRow = variableRows.find(row => row.textContent.includes('company_name'));
        expect(companyNameRow).toHaveTextContent('Reset');
        
        // email_domain (not customized) should not have reset button
        const emailDomainRow = variableRows.find(row => row.textContent.includes('email_domain'));
        expect(emailDomainRow).not.toHaveTextContent('Reset');
      });
    });

    it('should confirm before resetting individual variable', async () => {
      // Mock window.confirm
      window.confirm = jest.fn(() => true);
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const resetButton = screen.getByText('Reset');
        fireEvent.click(resetButton);
        
        expect(window.confirm).toHaveBeenCalledWith(
          'Reset variable "company_name" to its default value?'
        );
      });
    });

    it('should reset individual variable when confirmed', async () => {
      window.confirm = jest.fn(() => true);
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const resetButton = screen.getByText('Reset');
        fireEvent.click(resetButton);
      });
      
      await waitFor(() => {
        expect(apiClient.resetPackVariable).toHaveBeenCalledWith('Test Pack', 'company_name');
      });
    });

    it('should not reset variable when not confirmed', async () => {
      window.confirm = jest.fn(() => false);
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const resetButton = screen.getByText('Reset');
        fireEvent.click(resetButton);
        
        expect(apiClient.resetPackVariable).not.toHaveBeenCalled();
      });
    });

    it('should show reset all button when there are customized variables', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Reset All to Defaults')).toBeInTheDocument();
      });
    });

    it('should not show reset all button when no variables are customized', async () => {
      apiClient.getPackVariables.mockResolvedValue({
        data: { variables: {} }
      });
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        expect(screen.queryByText('Reset All to Defaults')).not.toBeInTheDocument();
      });
    });

    it('should confirm before resetting all variables', async () => {
      window.confirm = jest.fn(() => true);
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const resetAllButton = screen.getByText('Reset All to Defaults');
        fireEvent.click(resetAllButton);
        
        expect(window.confirm).toHaveBeenCalledWith(
          'Reset all variables for "Test Pack" to their default values?'
        );
      });
    });

    it('should reset all variables when confirmed', async () => {
      window.confirm = jest.fn(() => true);
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const resetAllButton = screen.getByText('Reset All to Defaults');
        fireEvent.click(resetAllButton);
      });
      
      await waitFor(() => {
        expect(apiClient.resetAllPackVariables).toHaveBeenCalledWith('Test Pack');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle save errors gracefully', async () => {
      apiClient.setPackVariable.mockRejectedValue(new Error('Save failed'));
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const editButton = screen.getAllByText('Edit')[0];
        fireEvent.click(editButton);
        
        const input = screen.getByDisplayValue('Custom Corp');
        fireEvent.change(input, { target: { value: 'New Corp' } });
        
        const saveButton = screen.getByText('Save');
        fireEvent.click(saveButton);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument();
        expect(screen.getByText(/Save failed/)).toBeInTheDocument();
      });
    });

    it('should handle reset errors gracefully', async () => {
      apiClient.resetPackVariable.mockRejectedValue(new Error('Reset failed'));
      window.confirm = jest.fn(() => true);
      
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const resetButton = screen.getByText('Reset');
        fireEvent.click(resetButton);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument();
        expect(screen.getByText(/Reset failed/)).toBeInTheDocument();
      });
    });

    it('should disable buttons during save operation', async () => {
      // Fix for the hanging test - ensure all promises resolve
      apiClient.setPackVariable.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({}), 100))
      );
      
      render(<VariableManager {...mockProps} />);
      
      // Wait for the component to load
      await waitFor(() => {
        expect(screen.queryByText('Loading variables...')).not.toBeInTheDocument();
      });
      
      // Find and click the edit button
      const editButton = screen.getAllByText('Edit')[0];
      fireEvent.click(editButton);
      
      // Change the input value
      const input = screen.getByDisplayValue('Custom Corp');
      fireEvent.change(input, { target: { value: 'New Corp' } });
      
      // Click save button
      const saveButton = screen.getByText('Save');
      fireEvent.click(saveButton);
      
      // Check that the UI shows saving state
      await waitFor(() => {
        expect(screen.getByText('Saving...')).toBeInTheDocument();
        expect(screen.getByText('Cancel')).toBeDisabled();
      });
      
      // Wait for the save operation to complete
      await waitFor(() => {
        expect(apiClient.setPackVariable).toHaveBeenCalled();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const modal = screen.getByRole('dialog');
        expect(modal).toBeInTheDocument();
      });
    });

    it('should focus input when entering edit mode', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const editButton = screen.getAllByText('Edit')[0];
        fireEvent.click(editButton);
        
        const input = screen.getByDisplayValue('Custom Corp');
        expect(input).toHaveFocus();
      });
    });

    it('should handle keyboard navigation', async () => {
      render(<VariableManager {...mockProps} />);
      
      await waitFor(() => {
        const editButton = screen.getAllByText('Edit')[0];
        fireEvent.click(editButton);
        
        const input = screen.getByDisplayValue('Custom Corp');
        fireEvent.keyPress(input, { key: 'Enter', code: 'Enter' });
        
        // Should trigger save on Enter key
        expect(apiClient.setPackVariable).toHaveBeenCalled();
      });
    });
  });

  afterEach(() => {
    // Clean up window.confirm mock
    if (window.confirm && window.confirm.mockRestore) {
      window.confirm.mockRestore();
    }
  });
});