import React, { useState, useEffect } from 'react';
import DashboardLayoutManager from '../components/DashboardLayoutManager';
import { getTimelineEvents } from '../api/client';

const TimelinePage = ({ isEditing, onSaveLayout, onCancelEdit, currentDashboard }) => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [selectedEventType, setSelectedEventType] = useState(null);
  const [tooltipEvent, setTooltipEvent] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        setLoading(true);
        const response = await getTimelineEvents();
        // Sort events by timestamp in descending order (newest first)
        const sortedEvents = response.data.sort((a, b) => 
          new Date(b.timestamp) - new Date(a.timestamp)
        );
        setEvents(sortedEvents);
        setError(null);
      } catch (err) {
        setError("Failed to fetch timeline events. Please ensure the core service is running.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
    // Set up polling to refresh events every 5 seconds
    const intervalId = setInterval(fetchEvents, 5000);
    return () => clearInterval(intervalId);
  }, []);

  // Group events by date for the horizontal timeline
  const groupedEvents = events.reduce((groups, event) => {
    const date = new Date(event.timestamp).toLocaleDateString();
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(event);
    return groups;
  }, {});

  // Get unique event types for filtering
  const eventTypes = [...new Set(events.map(event => event.event_type))];

  // Filter events based on selection
  const filteredEvents = selectedEvent
    ? events.filter(event => event.id === selectedEvent)
    : selectedEventType 
      ? events.filter(event => event.event_type === selectedEventType)
      : events;

  const handleEventClick = (event) => {
    // If the event is already selected, deselect it
    // Otherwise, select it and clear any event type filter
    if (event.id === selectedEvent) {
      setSelectedEvent(null);
    } else {
      setSelectedEvent(event.id);
      setSelectedEventType(null); // Clear event type filter when selecting a specific event
    }
  };

  const handleEventTypeClick = (eventType) => {
    // If the event type is already selected, deselect it
    // Otherwise, select it and clear any specific event selection
    if (eventType === selectedEventType) {
      setSelectedEventType(null);
    } else {
      setSelectedEventType(eventType);
      setSelectedEvent(null); // Clear selected event when filtering by event type
    }
  };

  // Format timestamp to a readable format
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Format date for the horizontal timeline
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };
  
  // Handle tooltip display
  const handleMouseEnter = (event, e) => {
    setTooltipEvent(event);
    updateTooltipPosition(e);
  };
  
  const handleMouseLeave = () => {
    setTooltipEvent(null);
  };
  
  const handleMouseMove = (e) => {
    if (tooltipEvent) {
      updateTooltipPosition(e);
    }
  };
  
  const updateTooltipPosition = (e) => {
    // Get viewport dimensions
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Calculate tooltip dimensions (approximate)
    const tooltipWidth = 350;
    const tooltipHeight = 150;
    
    // Calculate initial position (slightly above and to the right of cursor)
    let x = e.clientX + 10;
    let y = e.clientY - 10;
    
    // Adjust if tooltip would go off right edge
    if (x + tooltipWidth > viewportWidth) {
      x = e.clientX - tooltipWidth - 10;
    }
    
    // Adjust if tooltip would go off bottom edge
    if (y + tooltipHeight > viewportHeight) {
      y = e.clientY - tooltipHeight - 10;
    }
    
    // Adjust if tooltip would go off top edge
    if (y < 0) {
      y = 10;
    }
    
    // Set the position
    setTooltipPosition({ x, y });
  };

  return (
    <div className="timeline-container">
      <DashboardLayoutManager 
        isEditing={isEditing} 
        onSaveLayout={onSaveLayout} 
        onCancelEdit={onCancelEdit}
        currentDashboard={currentDashboard}
      >
        <div className="module-container size-xlarge" module_id="timeline-events">
          <h2>MCP Activity Timeline</h2>
          
          {loading && events.length === 0 ? (
            <p>Loading timeline events...</p>
          ) : error ? (
            <p className="error-message">{error}</p>
          ) : events.length === 0 ? (
            <p>No timeline events found. Actions performed by the MCP client will appear here.</p>
          ) : (
            <>
              {/* Horizontal Timeline */}
              <div className="horizontal-timeline">
                <div className="event-types">
                  {eventTypes.map(eventType => (
                    <div 
                      key={eventType}
                      className={`event-type ${selectedEventType === eventType ? 'selected' : ''}`}
                      onClick={() => handleEventTypeClick(eventType)}
                    >
                      {eventType}
                    </div>
                  ))}
                  {selectedEventType && (
                    <div 
                      className="event-type clear-filter"
                      onClick={() => setSelectedEventType(null)}
                    >
                      Clear Type Filter
                    </div>
                  )}
                  {selectedEvent && (
                    <div 
                      className="event-type clear-filter"
                      onClick={() => setSelectedEvent(null)}
                    >
                      Clear Event Selection
                    </div>
                  )}
                </div>
                <div className="timeline-dates">
                  {Object.entries(groupedEvents).map(([date, dateEvents]) => (
                    <div key={date} className="timeline-date-group">
                      <div className="timeline-date">{formatDate(date)}</div>
                      <div className="timeline-date-events">
                        {dateEvents.map(event => (
                          <div 
                            key={event.id}
                            className={`timeline-date-event ${event.event_type} ${selectedEvent === event.id ? 'selected' : ''}`}
                            onClick={() => handleEventClick(event)}
                            onMouseEnter={(e) => handleMouseEnter(event, e)}
                            onMouseLeave={handleMouseLeave}
                            onMouseMove={handleMouseMove}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Vertical Timeline */}
              <div className="vertical-timeline">
                {selectedEvent && (
                  <div className="selected-event-indicator">
                    Showing only the selected event. <button onClick={() => setSelectedEvent(null)}>Show All</button>
                  </div>
                )}
                <div className="timeline-line"></div>
                <div className="timeline-events">
                  {filteredEvents.map(event => (
                    <div 
                      key={event.id}
                      className={`timeline-event ${selectedEvent === event.id ? 'selected' : ''}`}
                      onClick={() => handleEventClick(event)}
                    >
                      <div className={`timeline-dot ${event.event_type}`}></div>
                      <div className="timeline-content">
                        <div className="timeline-header">
                          <h3>{event.title}</h3>
                          <span className="timeline-time">{formatTimestamp(event.timestamp)}</span>
                        </div>
                        <div className="timeline-body">
                          <p>{event.description}</p>
                          {event.details && (
                            <div className="timeline-details">
                              <pre>{JSON.stringify(event.details, null, 2)}</pre>
                            </div>
                          )}
                        </div>
                        <div className="timeline-footer">
                          <span className="timeline-type">{event.event_type}</span>
                          {event.status && (
                            <span className={`timeline-status ${event.status}`}>{event.status}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </DashboardLayoutManager>
      
      {/* Custom Tooltip */}
      {tooltipEvent && (
        <div 
          className="custom-tooltip"
          style={{
            left: `${tooltipPosition.x}px`,
            top: `${tooltipPosition.y}px`
          }}
        >
          <div className="tooltip-header">
            <span className={`tooltip-dot ${tooltipEvent.event_type}`}></span>
            <h4>{tooltipEvent.title}</h4>
          </div>
          <p>{tooltipEvent.description}</p>
          <div className="tooltip-footer">
            <span className="tooltip-time">
              {new Date(tooltipEvent.timestamp).toLocaleDateString([], {month: 'short', day: 'numeric', year: 'numeric'})} at {formatTimestamp(tooltipEvent.timestamp)}
            </span>
            {tooltipEvent.status && (
              <span className={`tooltip-status ${tooltipEvent.status}`}>{tooltipEvent.status}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelinePage;