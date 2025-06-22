import React, { useState, useRef, useEffect } from 'react';

const DashboardSelector = ({ currentDashboard, onDashboardChange }) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const selectorRef = useRef(null);

  // Available dashboards
  const dashboards = [
    { id: 'state', label: 'State' },
    { id: 'timeline', label: 'Timeline' }
  ];

  // Get the current dashboard label
  const currentDashboardLabel = dashboards.find(d => d.id === currentDashboard)?.label || 'State';

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
      >
        <span className="dashboard-selector-label">{currentDashboardLabel}</span>
        <span className="dashboard-selector-icon">▼</span>
      </div>
      {isDropdownOpen && (
        <div 
          ref={dropdownRef}
          className="dashboard-selector-dropdown"
        >
          {dashboards.map((dashboard) => (
            <button
              key={dashboard.id}
              className={`dashboard-option ${dashboard.id === currentDashboard ? 'active' : ''}`}
              onClick={() => handleDashboardSelect(dashboard.id)}
            >
              {dashboard.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default DashboardSelector;