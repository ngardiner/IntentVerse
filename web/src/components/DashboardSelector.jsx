import React, { useState, useRef, useEffect } from 'react';
import { getModulesStatus } from '../api/client';

const DashboardSelector = ({ currentDashboard, onDashboardChange }) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [availableDashboards, setAvailableDashboards] = useState([
    { id: 'state', label: 'State', icon: '⚡', description: 'View and manage module states' }
  ]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);
  const selectorRef = useRef(null);

  // All possible dashboards with their metadata
  const allDashboards = [
    { id: 'state', label: 'State', icon: '⚡', description: 'View and manage module states', alwaysAvailable: true },
    { id: 'timeline', label: 'Timeline', icon: '📋', description: 'View events and activity', moduleRequired: 'timeline' }
  ];

  // Load available dashboards based on enabled modules
  useEffect(() => {
    const loadAvailableDashboards = async () => {
      try {
        setLoading(true);
        const response = await getModulesStatus();
        const modules = response.data.modules;
        
        const available = allDashboards.filter(dashboard => {
          // Always include dashboards that don't require modules
          if (dashboard.alwaysAvailable) {
            return true;
          }
          
          // Include dashboards whose required module is enabled and loaded
          if (dashboard.moduleRequired) {
            const module = modules[dashboard.moduleRequired];
            return module && module.is_enabled && module.is_loaded;
          }
          
          return false;
        });
        
        setAvailableDashboards(available);
      } catch (error) {
        console.error('Failed to load module status:', error);
        // Fallback to just the state dashboard
        setAvailableDashboards([allDashboards[0]]);
      } finally {
        setLoading(false);
      }
    };

    loadAvailableDashboards();
  }, []);

  // Get the current dashboard info
  const currentDashboardInfo = availableDashboards.find(d => d.id === currentDashboard) || availableDashboards[0];

  useEffect(() => {
    // Function to handle clicks outside the dropdown
    const handleClickOutside = (event) => {
      if (
        isDropdownOpen &&
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target) &&
        selectorRef.current &&
        !selectorRef.current.contains(event.target)
      ) {
        setIsDropdownOpen(false);
      }
    };

    // Function to handle keyboard events
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && isDropdownOpen) {
        setIsDropdownOpen(false);
      }
    };

    // Add event listeners when dropdown is open
    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }

    // Clean up the event listeners
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isDropdownOpen]);

  const toggleDropdown = () => {
    setIsDropdownOpen(!isDropdownOpen);
  };

  const handleDashboardSelect = (dashboardId) => {
    setIsDropdownOpen(false);
    if (dashboardId !== currentDashboard) {
      onDashboardChange(dashboardId);
    }
  };

  return (
    <div className="dashboard-selector">
      <div 
        ref={selectorRef}
        className="dashboard-selector-button"
        onClick={toggleDropdown}
        aria-haspopup="true"
        aria-expanded={isDropdownOpen}
        role="button"
        tabIndex={0}
        aria-disabled={loading}
      >
        <div className="dashboard-selector-content">
          <span className="dashboard-selector-icon">{currentDashboardInfo?.icon || '⚡'}</span>
          <span className="dashboard-selector-label">{currentDashboardInfo?.label || 'State'}</span>
        </div>
        <span className="dashboard-selector-arrow">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </span>
      </div>
      {isDropdownOpen && (
        <div 
          ref={dropdownRef}
          className="dashboard-selector-dropdown"
        >
          <div className="dashboard-dropdown-header">
            <span>Switch Dashboard</span>
          </div>
          {availableDashboards.map((dashboard) => (
            <button
              key={dashboard.id}
              className={`dashboard-option ${dashboard.id === currentDashboard ? 'active' : ''}`}
              onClick={() => handleDashboardSelect(dashboard.id)}
            >
              <div className="dashboard-option-content">
                <div className="dashboard-option-main">
                  <span className="dashboard-option-icon">{dashboard.icon}</span>
                  <span className="dashboard-option-label">{dashboard.label}</span>
                  {dashboard.id === currentDashboard && (
                    <span className="dashboard-option-current">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M13.5 4.5L6 12L2.5 8.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </span>
                  )}
                </div>
                <div className="dashboard-option-description">{dashboard.description}</div>
              </div>
            </button>
          ))}
          {availableDashboards.length === 1 && (
            <div className="dashboard-dropdown-footer">
              <span>Enable modules in Settings to see more dashboards</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DashboardSelector;