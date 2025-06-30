import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Annotated, Union
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, status

from ...state_manager import state_manager
from ...auth import get_current_user_or_service, get_token_from_cookie_or_header
from ...models import User
from ..base_tool import BaseTool
from ...websocket_manager import manager as websocket_manager

# Create a router for the timeline endpoints
router = APIRouter(
    prefix="/api/v1/timeline",
    tags=["timeline"],
    responses={404: {"description": "Not found"}},
)

# Initialize the state manager for the timeline module

# Initialize the timeline state if it doesn't exist
if not state_manager.get("timeline"):
    state_manager.set("timeline", {"events": []})


def get_events() -> List[Dict[str, Any]]:
    """Get all timeline events."""
    state = state_manager.get("timeline") or {}
    return state.get("events", [])


async def broadcast_event(event: Dict[str, Any]):
    """
    Broadcast an event to all connected WebSocket clients.
    
    Args:
        event: The event to broadcast
    """
    try:
        await websocket_manager.broadcast(
            {
                "type": "timeline_event",
                "event": event
            },
            channel="timeline"
        )
        logging.debug(f"Broadcasted timeline event: {event['title']}")
    except Exception as e:
        logging.error(f"Failed to broadcast timeline event: {e}")


def add_event(
    event_type: str,
    title: str,
    description: str,
    details: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Add a new event to the timeline.

    Args:
        event_type: The type of event (e.g., tool_execution, system, error)
        title: A short title for the event
        description: A longer description of the event
        details: Optional additional details about the event (e.g., tool parameters)
        status: Optional status of the event (e.g., success, error, pending)

    Returns:
        The newly created event
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    event = {
        "id": event_id,
        "event_type": event_type,
        "title": title,
        "description": description,
        "timestamp": timestamp,
        "status": status,
    }

    if details:
        event["details"] = details

    # Get the current events
    state = state_manager.get("timeline") or {}
    events = state.get("events", [])

    # Add the new event
    events.append(event)

    # Limit the number of events to 1000 to prevent excessive memory usage
    if len(events) > 1000:
        events = events[-1000:]

    # Update the state
    state["events"] = events
    state_manager.set("timeline", state)

    logging.info(f"Added timeline event: {title}")
    
    # Broadcast the event via WebSockets asynchronously
    # We need to run this in a separate task since this function is synchronous
    asyncio.create_task(broadcast_event(event))
    
    return event


# API endpoint to get all events
@router.get("/events")
async def get_timeline_events(
    current_user_or_service: Annotated[
        Union[User, str], Depends(get_current_user_or_service)
    ],
    event_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get timeline events, optionally filtered by event_type.

    Args:
        current_user_or_service: The authenticated user or service
        event_type: Optional filter for event type
        limit: Maximum number of events to return

    Returns:
        List of timeline events
    """
    if limit <= 0:
        return []

    events = get_events()

    # Filter by event_type if provided
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]

    # Sort by timestamp (newest first)
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # Limit the number of events
    return events[:limit]


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket endpoint for real-time timeline events.
    
    Args:
        websocket: The WebSocket connection
        token: The authentication token (optional)
    """
    # Authenticate the WebSocket connection
    user = None
    if token:
        try:
            user = await get_token_from_cookie_or_header(token=token)
        except Exception as e:
            logging.warning(f"WebSocket authentication failed: {e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    
    # Accept the connection
    try:
        await websocket_manager.connect(websocket, channel="timeline")
        
        # Send the last 10 events immediately after connection
        events = get_events()
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        recent_events = events[:10]
        
        await websocket.send_json({
            "type": "initial_events",
            "events": recent_events
        })
        
        # Keep the connection alive
        while True:
            # Wait for messages from the client (ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


# Function to log tool executions
def log_tool_execution(
    tool_name: str, parameters: Dict[str, Any], result: Dict[str, Any]
) -> None:
    """
    Log a tool execution to the timeline.

    Args:
        tool_name: The name of the tool being executed
        parameters: The parameters passed to the tool
        result: The result of the tool execution
    """
    # Skip logging timeline tools to avoid recursion
    if tool_name.startswith("timeline."):
        return None

    status = result.get("status", "unknown")
    if status == "pending":
        title = f"Tool Executing: {tool_name}"
        description = (
            f"The tool '{tool_name}' is being executed with the provided parameters."
        )
    else:
        title = f"Tool Executed: {tool_name}"
        description = (
            f"The tool '{tool_name}' was executed with the provided parameters."
        )

    add_event(
        event_type="tool_execution",
        title=title,
        description=description,
        details={"tool_name": tool_name, "parameters": parameters, "result": result},
        status=status,
    )


# Function to log system events
def log_system_event(
    title: str, description: str, details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a system event to the timeline.

    Args:
        title: The title of the event
        description: A description of the event
        details: Optional additional details
    """
    add_event(
        event_type="system", title=title, description=description, details=details
    )


# Function to log errors
def log_error(
    title: str, description: str, details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an error to the timeline.

    Args:
        title: The title of the error
        description: A description of the error
        details: Optional additional details
    """
    add_event(
        event_type="error",
        title=title,
        description=description,
        details=details,
        status="error",
    )


class TimelineTool(BaseTool):
    """
    Timeline tool for logging and tracking events in the system.
    This tool provides functionality to log tool executions, system events, and errors.
    """

    def __init__(self, state_manager: Any):
        super().__init__(state_manager)
        # Initialize the timeline state if it doesn't exist
        if not self.state_manager.get("timeline"):
            self.state_manager.set("timeline", {"events": []})

    def get_ui_schema(self) -> Dict[str, Any]:
        """Returns the UI schema for the timeline module."""
        try:
            from .schema import UI_SCHEMA

            return UI_SCHEMA
        except ImportError:
            # Fallback if schema file doesn't exist
            return {
                "name": "timeline",
                "displayName": "Timeline",
                "description": "Timeline tool for logging and tracking events in the system",
                "version": "1.0.0",
                "components": [],
            }

    def get_events(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get timeline events, optionally filtered by event_type.

        Args:
            event_type: Optional filter for event type
            limit: Maximum number of events to return

        Returns:
            List of timeline events
        """
        if limit <= 0:
            return []

        state = self.state_manager.get("timeline") or {}
        events = state.get("events", [])

        # Filter by event_type if provided
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]

        # Sort by timestamp (newest first)
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Limit the number of events
        return events[:limit]

    def add_event(
        self,
        event_type: str,
        title: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a new event to the timeline.

        Args:
            event_type: The type of event (e.g., tool_execution, system, error)
            title: A short title for the event
            description: A longer description of the event
            details: Optional additional details about the event (e.g., tool parameters)
            status: Optional status of the event (e.g., success, error, pending)

        Returns:
            The newly created event
        """
        return add_event(event_type, title, description, details, status)

    def clear_events(self) -> str:
        """
        Clear all timeline events.

        Returns:
            Success message
        """
        self.state_manager.set("timeline", {"events": []})
        return "Timeline events cleared successfully"
