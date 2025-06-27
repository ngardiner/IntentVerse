# Timeline API

The Timeline API provides event logging and timeline management capabilities for IntentVerse. It tracks system events, tool executions, errors, and user activities in a chronological timeline.

## Overview

The Timeline system automatically logs:
- **Tool Executions**: All tool calls and their results
- **System Events**: Service starts/stops, configuration changes
- **Error Events**: System errors and failures
- **User Activities**: Login/logout, permission changes
- **Custom Events**: Application-specific events

## Authentication

Timeline endpoints require authentication via JWT token or API key. Permission requirements vary by endpoint.

## Timeline Endpoints

### Get Timeline Events

**GET** `/api/v1/timeline/events`

Retrieves timeline events with optional filtering.

**Parameters:**
- `event_type` (query, optional): Filter by event type
- `limit` (query, optional): Maximum number of events to return (default: 100)

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `timeline.read`

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "tool_execution",
    "title": "Tool Executed: filesystem.read_file",
    "description": "The tool 'filesystem.read_file' was executed with the provided parameters.",
    "timestamp": "2024-01-01T12:30:00Z",
    "status": "success",
    "details": {
      "tool_name": "filesystem.read_file",
      "parameters": {
        "file_path": "/home/user/document.txt"
      },
      "result": {
        "status": "success",
        "result": "File content here..."
      }
    }
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "event_type": "system",
    "title": "Core Service Started",
    "description": "The IntentVerse Core Engine has been started and is ready to accept connections.",
    "timestamp": "2024-01-01T12:00:00Z",
    "status": null,
    "details": null
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "event_type": "error",
    "title": "File Not Found Error",
    "description": "Attempted to read non-existent file",
    "timestamp": "2024-01-01T12:25:00Z",
    "status": "error",
    "details": {
      "error_type": "FileNotFoundError",
      "file_path": "/invalid/path.txt",
      "tool_name": "filesystem.read_file"
    }
  }
]
```

**Example Requests:**

```bash
# Get all events (last 100)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/timeline/events"

# Get only tool execution events
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/timeline/events?event_type=tool_execution"

# Get last 50 system events
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/timeline/events?event_type=system&limit=50"
```

## Event Types

### Tool Execution Events

**Event Type:** `tool_execution`

Logged automatically when tools are executed via the MCP interface.

**Example Event:**
```json
{
  "id": "uuid",
  "event_type": "tool_execution",
  "title": "Tool Executed: database.execute_query",
  "description": "The tool 'database.execute_query' was executed with the provided parameters.",
  "timestamp": "2024-01-01T12:30:00Z",
  "status": "success",
  "details": {
    "tool_name": "database.execute_query",
    "parameters": {
      "query": "SELECT COUNT(*) FROM users",
      "fetch_results": true
    },
    "result": {
      "status": "success",
      "result": [{"COUNT(*)": 150}]
    }
  }
}
```

### System Events

**Event Type:** `system`

Logged for system-level activities and changes.

**Common System Events:**
- Service startup/shutdown
- Module enable/disable
- Configuration changes
- Database migrations
- Content pack loading

**Example Event:**
```json
{
  "id": "uuid",
  "event_type": "system",
  "title": "Module Enabled",
  "description": "The email module has been enabled",
  "timestamp": "2024-01-01T12:15:00Z",
  "status": null,
  "details": {
    "module_name": "email",
    "action": "enabled",
    "user": "admin"
  }
}
```

### Error Events

**Event Type:** `error`

Logged when errors occur in the system.

**Example Event:**
```json
{
  "id": "uuid",
  "event_type": "error",
  "title": "Database Connection Failed",
  "description": "Failed to connect to the database",
  "timestamp": "2024-01-01T12:20:00Z",
  "status": "error",
  "details": {
    "error_type": "ConnectionError",
    "error_message": "Connection timeout after 30 seconds",
    "module": "database",
    "retry_count": 3
  }
}
```

### User Activity Events

**Event Type:** `user_activity`

Logged for significant user actions (via audit system).

**Example Event:**
```json
{
  "id": "uuid",
  "event_type": "user_activity",
  "title": "User Login",
  "description": "User 'john_doe' logged in successfully",
  "timestamp": "2024-01-01T12:10:00Z",
  "status": "success",
  "details": {
    "username": "john_doe",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "action": "login"
  }
}
```

## Tool Integration

The Timeline API can be accessed programmatically through the MCP interface:

### Get Events via Tool

**Tool:** `timeline.get_events`

**Parameters:**
- `event_type` (string, optional): Filter by event type
- `limit` (integer, optional): Maximum number of events to return

**Example:**
```json
{
  "tool_name": "timeline.get_events",
  "parameters": {
    "event_type": "tool_execution",
    "limit": 25
  }
}
```

### Add Custom Events via Tool

**Tool:** `timeline.add_event`

**Parameters:**
- `event_type` (string, required): Type of event
- `title` (string, required): Event title
- `description` (string, required): Event description
- `details` (object, optional): Additional event details
- `status` (string, optional): Event status

**Example:**
```json
{
  "tool_name": "timeline.add_event",
  "parameters": {
    "event_type": "custom",
    "title": "Data Processing Complete",
    "description": "Finished processing user data batch",
    "details": {
      "batch_id": "batch_001",
      "records_processed": 1500,
      "processing_time": "45.2s"
    },
    "status": "success"
  }
}
```

### Clear Events via Tool

**Tool:** `timeline.clear_events`

Clears all timeline events (requires appropriate permissions).

**Parameters:** None

**Example:**
```json
{
  "tool_name": "timeline.clear_events",
  "parameters": {}
}
```

## Event Structure

### Base Event Schema

All timeline events follow this base structure:

```json
{
  "id": "string (UUID)",
  "event_type": "string",
  "title": "string",
  "description": "string", 
  "timestamp": "string (ISO 8601)",
  "status": "string|null",
  "details": "object|null"
}
```

### Field Descriptions

- **id**: Unique identifier for the event (UUID)
- **event_type**: Category of event (tool_execution, system, error, user_activity, custom)
- **title**: Short, descriptive title for the event
- **description**: Longer description of what happened
- **timestamp**: When the event occurred (ISO 8601 format)
- **status**: Optional status (success, error, pending, etc.)
- **details**: Optional additional data specific to the event type

### Status Values

Common status values used in events:

- `success`: Operation completed successfully
- `error`: Operation failed with an error
- `pending`: Operation is in progress
- `warning`: Operation completed with warnings
- `cancelled`: Operation was cancelled
- `timeout`: Operation timed out

## Filtering and Querying

### Event Type Filtering

Filter events by type using the `event_type` parameter:

```bash
# Tool executions only
GET /api/v1/timeline/events?event_type=tool_execution

# System events only  
GET /api/v1/timeline/events?event_type=system

# Error events only
GET /api/v1/timeline/events?event_type=error
```

### Limiting Results

Control the number of events returned:

```bash
# Get last 10 events
GET /api/v1/timeline/events?limit=10

# Get last 5 error events
GET /api/v1/timeline/events?event_type=error&limit=5
```

### Event Ordering

Events are always returned in reverse chronological order (newest first).

## Performance Considerations

### Event Retention

- Timeline maintains up to 1000 events in memory
- Older events are automatically purged when the limit is exceeded
- For long-term storage, consider exporting events periodically

### Query Performance

- Filtering by event type is efficient
- Large limit values may impact performance
- Consider pagination for large result sets

## Integration Examples

### Python Timeline Client

```python
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

class TimelineClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get timeline events with optional filtering."""
        params = {'limit': limit}
        if event_type:
            params['event_type'] = event_type
        
        response = requests.get(
            f"{self.base_url}/api/v1/timeline/events",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent error events."""
        return self.get_events(event_type='error', limit=limit)
    
    def get_tool_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent tool execution events."""
        return self.get_events(event_type='tool_execution', limit=limit)
    
    def add_custom_event(self, title: str, description: str, 
                        details: Optional[Dict[str, Any]] = None,
                        status: Optional[str] = None) -> Dict[str, Any]:
        """Add a custom event to the timeline."""
        # Use the MCP interface to add events
        payload = {
            'tool_name': 'timeline.add_event',
            'parameters': {
                'event_type': 'custom',
                'title': title,
                'description': description,
                'details': details,
                'status': status
            }
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/execute",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

# Usage example
client = TimelineClient('http://localhost:8000', 'your-token')

# Get recent events
events = client.get_events(limit=20)
print(f"Retrieved {len(events)} events")

# Get recent errors
errors = client.get_recent_errors()
if errors:
    print(f"Found {len(errors)} recent errors:")
    for error in errors:
        print(f"  - {error['title']}: {error['description']}")

# Add a custom event
result = client.add_custom_event(
    title="Backup Completed",
    description="Daily database backup completed successfully",
    details={
        "backup_size": "2.5GB",
        "duration": "15 minutes",
        "backup_location": "/backups/db_2024-01-01.sql"
    },
    status="success"
)
print(f"Added custom event: {result}")
```

### JavaScript Timeline Integration

```javascript
class TimelineClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }
  
  async getEvents(eventType = null, limit = 100) {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (eventType) {
      params.append('event_type', eventType);
    }
    
    const response = await fetch(
      `${this.baseUrl}/api/v1/timeline/events?${params}`,
      { headers: this.headers }
    );
    
    if (!response.ok) {
      throw new Error(`Failed to get events: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async getEventsSince(timestamp, eventType = null) {
    const events = await this.getEvents(eventType, 1000);
    return events.filter(event => 
      new Date(event.timestamp) > new Date(timestamp)
    );
  }
  
  async monitorEvents(callback, interval = 5000) {
    let lastTimestamp = new Date().toISOString();
    
    setInterval(async () => {
      try {
        const newEvents = await this.getEventsSince(lastTimestamp);
        if (newEvents.length > 0) {
          callback(newEvents);
          lastTimestamp = newEvents[0].timestamp;
        }
      } catch (error) {
        console.error('Error monitoring events:', error);
      }
    }, interval);
  }
  
  async addCustomEvent(title, description, details = null, status = null) {
    const payload = {
      tool_name: 'timeline.add_event',
      parameters: {
        event_type: 'custom',
        title: title,
        description: description,
        details: details,
        status: status
      }
    };
    
    const response = await fetch(`${this.baseUrl}/api/v1/execute`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      throw new Error(`Failed to add event: ${response.statusText}`);
    }
    
    return response.json();
  }
}

// Usage example
const timeline = new TimelineClient('http://localhost:8000', 'your-token');

// Get recent tool executions
const toolEvents = await timeline.getEvents('tool_execution', 20);
console.log(`Recent tool executions: ${toolEvents.length}`);

// Monitor for new events
timeline.monitorEvents((newEvents) => {
  console.log(`New events detected: ${newEvents.length}`);
  newEvents.forEach(event => {
    console.log(`  ${event.event_type}: ${event.title}`);
  });
});

// Add a custom event
await timeline.addCustomEvent(
  'User Registration',
  'New user registered in the system',
  {
    username: 'new_user',
    email: 'user@example.com',
    registration_source: 'web_ui'
  },
  'success'
);
```

### React Timeline Component

```jsx
import React, { useState, useEffect } from 'react';
import { TimelineClient } from './timeline-client';

const TimelineView = ({ token }) => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  
  const timeline = new TimelineClient('http://localhost:8000', token);
  
  useEffect(() => {
    loadEvents();
  }, [filter]);
  
  const loadEvents = async () => {
    try {
      setLoading(true);
      const eventType = filter === 'all' ? null : filter;
      const eventData = await timeline.getEvents(eventType, 50);
      setEvents(eventData);
    } catch (error) {
      console.error('Failed to load events:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };
  
  const getEventIcon = (eventType, status) => {
    if (status === 'error') return '❌';
    if (eventType === 'tool_execution') return '🔧';
    if (eventType === 'system') return '⚙️';
    if (eventType === 'user_activity') return '👤';
    return '📝';
  };
  
  return (
    <div className="timeline-view">
      <div className="timeline-header">
        <h2>Timeline</h2>
        <select 
          value={filter} 
          onChange={(e) => setFilter(e.target.value)}
          className="event-filter"
        >
          <option value="all">All Events</option>
          <option value="tool_execution">Tool Executions</option>
          <option value="system">System Events</option>
          <option value="error">Errors</option>
          <option value="user_activity">User Activity</option>
        </select>
      </div>
      
      {loading ? (
        <div className="loading">Loading events...</div>
      ) : (
        <div className="timeline-events">
          {events.map(event => (
            <div key={event.id} className={`timeline-event ${event.status || ''}`}>
              <div className="event-header">
                <span className="event-icon">
                  {getEventIcon(event.event_type, event.status)}
                </span>
                <span className="event-title">{event.title}</span>
                <span className="event-timestamp">
                  {formatTimestamp(event.timestamp)}
                </span>
              </div>
              <div className="event-description">
                {event.description}
              </div>
              {event.details && (
                <details className="event-details">
                  <summary>Details</summary>
                  <pre>{JSON.stringify(event.details, null, 2)}</pre>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TimelineView;
```

## Best Practices

### Event Design

1. **Clear Titles**: Use descriptive, concise titles
2. **Detailed Descriptions**: Provide context in descriptions
3. **Structured Details**: Use consistent detail object structures
4. **Appropriate Status**: Set meaningful status values
5. **Relevant Information**: Include relevant context in details

### Performance

1. **Limit Queries**: Use appropriate limit values
2. **Filter Events**: Filter by event type when possible
3. **Batch Processing**: Process events in batches for better performance
4. **Caching**: Cache frequently accessed events
5. **Cleanup**: Regularly clean up old events if needed

### Monitoring

1. **Error Tracking**: Monitor error events for system health
2. **Performance Metrics**: Track tool execution times
3. **User Activity**: Monitor user behavior patterns
4. **System Health**: Watch for system event anomalies
5. **Alerting**: Set up alerts for critical events

### Security

1. **Sensitive Data**: Avoid logging sensitive information in details
2. **Access Control**: Ensure proper permissions for timeline access
3. **Audit Trail**: Maintain timeline integrity for audit purposes
4. **Data Retention**: Implement appropriate data retention policies
5. **Privacy**: Respect user privacy in event logging