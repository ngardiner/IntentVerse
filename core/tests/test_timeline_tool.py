"""
Unit tests for the Timeline module.
"""
import pytest
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.modules.timeline.tool import (
    get_events,
    add_event,
    log_tool_execution,
    log_system_event,
    log_error,
    router
)
from app.modules.timeline.sample_data import generate_sample_events
from app.state_manager import StateManager


class TestTimelineCore:
    """Test core timeline functionality (non-API functions)."""
    
    @pytest.fixture
    def mock_state_manager(self):
        """Create a mock state manager for testing."""
        mock_sm = Mock(spec=StateManager)
        mock_sm.get.return_value = {"events": []}
        mock_sm.set = Mock()
        return mock_sm
    
    @pytest.fixture(autouse=True)
    def setup_state_manager(self, mock_state_manager):
        """Setup state manager mock for all tests."""
        with patch('app.modules.timeline.tool.state_manager', mock_state_manager):
            yield mock_state_manager
    
    def test_get_events_empty_state(self, mock_state_manager):
        """Test getting events when state is empty."""
        mock_state_manager.get.return_value = None
        
        events = get_events()
        
        assert events == []
        mock_state_manager.get.assert_called_once_with("timeline")
    
    def test_get_events_with_existing_events(self, mock_state_manager):
        """Test getting events when events exist."""
        existing_events = [
            {
                "id": "test-id-1",
                "event_type": "system",
                "title": "Test Event",
                "description": "Test Description",
                "timestamp": "2023-01-01T00:00:00",
                "status": None
            }
        ]
        mock_state_manager.get.return_value = {"events": existing_events}
        
        events = get_events()
        
        assert events == existing_events
        mock_state_manager.get.assert_called_once_with("timeline")
    
    def test_add_event_basic(self, mock_state_manager):
        """Test adding a basic event."""
        mock_state_manager.get.return_value = {"events": []}
        
        with patch('app.modules.timeline.tool.uuid.uuid4') as mock_uuid, \
             patch('app.modules.timeline.tool.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="test-uuid")
            mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T00:00:00"
            
            event = add_event(
                event_type="test_type",
                title="Test Title",
                description="Test Description"
            )
            
            expected_event = {
                "id": "test-uuid",
                "event_type": "test_type",
                "title": "Test Title",
                "description": "Test Description",
                "timestamp": "2023-01-01T00:00:00",
                "status": None
            }
            
            assert event == expected_event
            mock_state_manager.set.assert_called_once_with("timeline", {
                "events": [expected_event]
            })
    
    def test_add_event_with_details_and_status(self, mock_state_manager):
        """Test adding an event with details and status."""
        mock_state_manager.get.return_value = {"events": []}
        
        with patch('app.modules.timeline.tool.uuid.uuid4') as mock_uuid, \
             patch('app.modules.timeline.tool.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="test-uuid")
            mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T00:00:00"
            
            details = {"key": "value", "number": 42}
            
            event = add_event(
                event_type="test_type",
                title="Test Title",
                description="Test Description",
                details=details,
                status="success"
            )
            
            expected_event = {
                "id": "test-uuid",
                "event_type": "test_type",
                "title": "Test Title",
                "description": "Test Description",
                "timestamp": "2023-01-01T00:00:00",
                "status": "success",
                "details": details
            }
            
            assert event == expected_event
    
    def test_add_event_limits_to_1000_events(self, mock_state_manager):
        """Test that adding events limits the total to 1000."""
        # Create 1000 existing events
        existing_events = []
        for i in range(1000):
            existing_events.append({
                "id": f"event-{i}",
                "event_type": "test",
                "title": f"Event {i}",
                "description": f"Description {i}",
                "timestamp": f"2023-01-01T{i:02d}:00:00",
                "status": None
            })
        
        mock_state_manager.get.return_value = {"events": existing_events}
        
        with patch('app.modules.timeline.tool.uuid.uuid4') as mock_uuid, \
             patch('app.modules.timeline.tool.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="new-event")
            mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-02T00:00:00"
            
            add_event(
                event_type="new_type",
                title="New Event",
                description="New Description"
            )
            
            # Verify that set was called with exactly 1000 events
            call_args = mock_state_manager.set.call_args[0]
            assert call_args[0] == "timeline"
            assert len(call_args[1]["events"]) == 1000
            
            # Verify the new event is the last one
            last_event = call_args[1]["events"][-1]
            assert last_event["id"] == "new-event"
            assert last_event["title"] == "New Event"
    
    def test_log_tool_execution_success(self, mock_state_manager):
        """Test logging a successful tool execution."""
        mock_state_manager.get.return_value = {"events": []}
        
        with patch('app.modules.timeline.tool.uuid.uuid4') as mock_uuid, \
             patch('app.modules.timeline.tool.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="tool-event")
            mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T00:00:00"
            
            parameters = {"param1": "value1", "param2": 42}
            result = {"status": "success", "data": "result_data"}
            
            log_tool_execution("filesystem.read_file", parameters, result)
            
            # Verify the event was added correctly
            call_args = mock_state_manager.set.call_args[0]
            event = call_args[1]["events"][0]
            
            assert event["event_type"] == "tool_execution"
            assert event["title"] == "Tool Executed: filesystem.read_file"
            assert "filesystem.read_file" in event["description"]
            assert event["status"] == "success"
            assert event["details"]["tool_name"] == "filesystem.read_file"
            assert event["details"]["parameters"] == parameters
            assert event["details"]["result"] == result
    
    def test_log_tool_execution_pending(self, mock_state_manager):
        """Test logging a pending tool execution."""
        mock_state_manager.get.return_value = {"events": []}
        
        with patch('app.modules.timeline.tool.uuid.uuid4') as mock_uuid, \
             patch('app.modules.timeline.tool.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="tool-event")
            mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T00:00:00"
            
            parameters = {"param1": "value1"}
            result = {"status": "pending"}
            
            log_tool_execution("database.execute_query", parameters, result)
            
            # Verify the event was added correctly
            call_args = mock_state_manager.set.call_args[0]
            event = call_args[1]["events"][0]
            
            assert event["title"] == "Tool Executing: database.execute_query"
            assert "is being executed" in event["description"]
            assert event["status"] == "pending"
    
    def test_log_tool_execution_skips_timeline_tools(self, mock_state_manager):
        """Test that timeline tools are not logged to avoid recursion."""
        log_tool_execution("timeline.get_events", {}, {"status": "success"})
        
        # Verify no state manager calls were made
        mock_state_manager.get.assert_not_called()
        mock_state_manager.set.assert_not_called()
    
    def test_log_system_event(self, mock_state_manager):
        """Test logging a system event."""
        mock_state_manager.get.return_value = {"events": []}
        
        with patch('app.modules.timeline.tool.uuid.uuid4') as mock_uuid, \
             patch('app.modules.timeline.tool.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="system-event")
            mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T00:00:00"
            
            details = {"component": "database", "version": "1.0"}
            
            log_system_event("System Started", "The system has started successfully", details)
            
            # Verify the event was added correctly
            call_args = mock_state_manager.set.call_args[0]
            event = call_args[1]["events"][0]
            
            assert event["event_type"] == "system"
            assert event["title"] == "System Started"
            assert event["description"] == "The system has started successfully"
            assert event["details"] == details
            assert event["status"] is None
    
    def test_log_error(self, mock_state_manager):
        """Test logging an error event."""
        mock_state_manager.get.return_value = {"events": []}
        
        with patch('app.modules.timeline.tool.uuid.uuid4') as mock_uuid, \
             patch('app.modules.timeline.tool.datetime') as mock_datetime:
            
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="error-event")
            mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T00:00:00"
            
            details = {"error_code": "404", "file": "/missing.txt"}
            
            log_error("File Not Found", "The requested file could not be found", details)
            
            # Verify the event was added correctly
            call_args = mock_state_manager.set.call_args[0]
            event = call_args[1]["events"][0]
            
            assert event["event_type"] == "error"
            assert event["title"] == "File Not Found"
            assert event["description"] == "The requested file could not be found"
            assert event["details"] == details
            assert event["status"] == "error"


class TestTimelineAPI:
    """Test timeline API endpoints."""
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events for testing."""
        return [
            {
                "id": "event-1",
                "event_type": "tool_execution",
                "title": "Tool Executed: filesystem.read_file",
                "description": "The tool 'filesystem.read_file' was executed",
                "timestamp": "2023-01-01T12:00:00",
                "status": "success",
                "details": {
                    "tool_name": "filesystem.read_file",
                    "parameters": {"path": "/test.txt"},
                    "result": {"status": "success", "content": "file content"}
                }
            },
            {
                "id": "event-2",
                "event_type": "system",
                "title": "System Started",
                "description": "The system has been started",
                "timestamp": "2023-01-01T11:00:00",
                "status": None
            },
            {
                "id": "event-3",
                "event_type": "error",
                "title": "File Not Found",
                "description": "The requested file was not found",
                "timestamp": "2023-01-01T10:00:00",
                "status": "error",
                "details": {"file": "/missing.txt"}
            }
        ]
    
    def test_get_timeline_events_success(self, authenticated_client, sample_events):
        """Test successful retrieval of timeline events."""
        with patch('app.modules.timeline.tool.get_events', return_value=sample_events):
            response = authenticated_client.get("/api/v1/timeline/events")
            
            assert response.status_code == 200
            data = response.json()
            
            # Events should be sorted by timestamp (newest first)
            assert len(data) == 3
            assert data[0]["id"] == "event-1"  # 12:00:00 - newest
            assert data[1]["id"] == "event-2"  # 11:00:00
            assert data[2]["id"] == "event-3"  # 10:00:00 - oldest
    
    def test_get_timeline_events_with_event_type_filter(self, authenticated_client, sample_events):
        """Test filtering events by event_type."""
        with patch('app.modules.timeline.tool.get_events', return_value=sample_events):
            response = authenticated_client.get("/api/v1/timeline/events?event_type=tool_execution")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should only return tool_execution events
            assert len(data) == 1
            assert data[0]["event_type"] == "tool_execution"
            assert data[0]["id"] == "event-1"
    
    def test_get_timeline_events_with_limit(self, authenticated_client, sample_events):
        """Test limiting the number of returned events."""
        with patch('app.modules.timeline.tool.get_events', return_value=sample_events):
            response = authenticated_client.get("/api/v1/timeline/events?limit=2")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should only return 2 events (newest first)
            assert len(data) == 2
            assert data[0]["id"] == "event-1"
            assert data[1]["id"] == "event-2"
    
    def test_get_timeline_events_with_event_type_and_limit(self, authenticated_client, sample_events):
        """Test combining event_type filter and limit."""
        # Add more tool_execution events to test limit
        extended_events = sample_events + [
            {
                "id": "event-4",
                "event_type": "tool_execution",
                "title": "Tool Executed: database.query",
                "description": "Database query executed",
                "timestamp": "2023-01-01T13:00:00",
                "status": "success"
            }
        ]
        
        with patch('app.modules.timeline.tool.get_events', return_value=extended_events):
            response = authenticated_client.get("/api/v1/timeline/events?event_type=tool_execution&limit=1")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should return only 1 tool_execution event (the newest)
            assert len(data) == 1
            assert data[0]["event_type"] == "tool_execution"
            assert data[0]["id"] == "event-4"  # Newest tool_execution event
    
    def test_get_timeline_events_empty_result(self, authenticated_client):
        """Test when no events exist."""
        with patch('app.modules.timeline.tool.get_events', return_value=[]):
            response = authenticated_client.get("/api/v1/timeline/events")
            
            assert response.status_code == 200
            data = response.json()
            assert data == []
    
    def test_get_timeline_events_no_matching_filter(self, authenticated_client, sample_events):
        """Test when no events match the filter."""
        with patch('app.modules.timeline.tool.get_events', return_value=sample_events):
            response = authenticated_client.get("/api/v1/timeline/events?event_type=nonexistent")
            
            assert response.status_code == 200
            data = response.json()
            assert data == []
    
    def test_get_timeline_events_invalid_limit(self, authenticated_client, sample_events):
        """Test with invalid limit parameter."""
        with patch('app.modules.timeline.tool.get_events', return_value=sample_events):
            # Test with negative limit
            response = authenticated_client.get("/api/v1/timeline/events?limit=-1")
            
            assert response.status_code == 200
            data = response.json()
            # Should return empty list for negative limit
            assert data == []
    
    def test_get_timeline_events_zero_limit(self, authenticated_client, sample_events):
        """Test with zero limit."""
        with patch('app.modules.timeline.tool.get_events', return_value=sample_events):
            response = authenticated_client.get("/api/v1/timeline/events?limit=0")
            
            assert response.status_code == 200
            data = response.json()
            # Should return empty list for zero limit
            assert data == []
    
    def test_get_timeline_events_authentication_required(self, client):
        """Test that authentication is required for the endpoint."""
        # Use client without authentication headers
        response = client.get("/api/v1/timeline/events")
        
        # Should return 401 or 403 for unauthenticated request
        assert response.status_code in [401, 403]
    
    def test_get_timeline_events_with_service_auth(self, service_client, sample_events):
        """Test that service authentication works for timeline endpoints."""
        with patch('app.modules.timeline.tool.get_events', return_value=sample_events):
            response = service_client.get("/api/v1/timeline/events")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3


class TestTimelineSampleData:
    """Test timeline sample data generation."""
    
    @pytest.fixture
    def mock_state_manager(self):
        """Create a mock state manager for testing."""
        mock_sm = Mock(spec=StateManager)
        mock_sm.get.return_value = {"events": []}
        mock_sm.set = Mock()
        return mock_sm
    
    @pytest.fixture(autouse=True)
    def setup_state_manager(self, mock_state_manager):
        """Setup state manager mock for all tests."""
        with patch('app.modules.timeline.tool.state_manager', mock_state_manager):
            yield mock_state_manager
    
    def test_generate_sample_events_default_count(self, mock_state_manager):
        """Test generating sample events with default count."""
        with patch('app.modules.timeline.tool.uuid.uuid4') as mock_uuid, \
             patch('app.modules.timeline.sample_data.datetime') as mock_datetime, \
             patch('random.randint') as mock_randint, \
             patch('random.choice') as mock_choice, \
             patch('random.choices') as mock_choices:
            
            # Setup mocks
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="sample-uuid")
            mock_datetime.utcnow.return_value = datetime(2023, 1, 1, 12, 0, 0)
            mock_randint.return_value = 1
            mock_choice.return_value = "filesystem.read_file"
            mock_choices.side_effect = [["tool_execution"], ["success"]]
            
            events = generate_sample_events()
            
            # Should generate 20 events by default
            assert len(events) == 20
            # Verify state manager was called to add events
            assert mock_state_manager.set.call_count == 20
    
    def test_generate_sample_events_custom_count(self, mock_state_manager):
        """Test generating sample events with custom count."""
        with patch('app.modules.timeline.tool.uuid.uuid4') as mock_uuid, \
             patch('app.modules.timeline.sample_data.datetime') as mock_datetime, \
             patch('random.randint') as mock_randint, \
             patch('random.choice') as mock_choice, \
             patch('random.choices') as mock_choices:
            
            # Setup mocks
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="sample-uuid")
            mock_datetime.utcnow.return_value = datetime(2023, 1, 1, 12, 0, 0)
            mock_randint.return_value = 1
            mock_choice.return_value = "filesystem.read_file"
            mock_choices.side_effect = [["tool_execution"], ["success"]] * 5
            
            events = generate_sample_events(count=5)
            
            # Should generate 5 events
            assert len(events) == 5
            # Verify state manager was called to add events
            assert mock_state_manager.set.call_count == 5
    
    def test_generate_sample_events_tool_execution_type(self, mock_state_manager):
        """Test generating tool_execution type events."""
        with patch('app.modules.timeline.tool.uuid.uuid4') as mock_uuid, \
             patch('app.modules.timeline.sample_data.datetime') as mock_datetime, \
             patch('random.randint') as mock_randint, \
             patch('random.choice') as mock_choice, \
             patch('random.choices') as mock_choices:
            
            # Setup mocks to always generate tool_execution events
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value="tool-uuid")
            mock_datetime.utcnow.return_value = datetime(2023, 1, 1, 12, 0, 0)
            mock_randint.return_value = 1
            mock_choice.return_value = "filesystem.read_file"
            mock_choices.side_effect = [["tool_execution"], ["success"]]
            
            events = generate_sample_events(count=1)
            
            assert len(events) == 1
            event = events[0]
            assert event["event_type"] == "tool_execution"
            assert "Tool Executed:" in event["title"]
            assert "filesystem.read_file" in event["title"]
            assert event["status"] == "success"
            assert "details" in event
            assert "tool_name" in event["details"]
            assert "parameters" in event["details"]
            assert "result" in event["details"]


class TestTimelineIntegration:
    """Test timeline integration with other components."""
    
    def test_timeline_router_included_in_main_app(self):
        """Test that timeline router is properly included in main app."""
        from app.main import app
        
        # Check that the timeline router is included
        timeline_routes = [route for route in app.routes if hasattr(route, 'path') and '/timeline' in route.path]
        assert len(timeline_routes) > 0
        
        # Check that the events endpoint exists
        events_routes = [route for route in timeline_routes if route.path.endswith('/events')]
        assert len(events_routes) > 0
    
    def test_timeline_logging_functions_importable(self):
        """Test that timeline logging functions can be imported."""
        from app.modules.timeline import log_tool_execution, log_system_event, log_error
        
        # Verify functions are callable
        assert callable(log_tool_execution)
        assert callable(log_system_event)
        assert callable(log_error)
    
    def test_timeline_ui_schema_structure(self):
        """Test that timeline UI schema has correct structure."""
        from app.modules.timeline.schema import UI_SCHEMA
        
        assert UI_SCHEMA["module_id"] == "timeline"
        assert UI_SCHEMA["display_name"] == "Timeline"
        assert UI_SCHEMA["size"] == "xlarge"
        assert "components" in UI_SCHEMA
        assert len(UI_SCHEMA["components"]) > 0
        
        # Check table component
        table_component = UI_SCHEMA["components"][0]
        assert table_component["component_type"] == "table"
        assert table_component["data_source_api"] == "/api/v1/timeline/events"
        assert "columns" in table_component
        assert len(table_component["columns"]) == 5  # timestamp, event_type, title, description, status