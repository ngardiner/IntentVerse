import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Annotated, Union
from fastapi import APIRouter, Depends, HTTPException

from ...state_manager import state_manager
from ...auth import get_current_user_or_service
from ...models import User

# Create a router for the timeline endpoints
router = APIRouter(
    prefix="/api/v1/timeline",
    tags=["timeline"],
    responses={404: {"description": "Not found"}},
)

# Initialize the state manager for the timeline module

# Initialize the timeline state if it doesn't exist
if not state_manager.get("timeline"):
    state_manager.set("timeline", {
        "events": []
    })

def get_events() -> List[Dict[str, Any]]:
    """Get all timeline events."""
    state = state_manager.get("timeline") or {}
    return state.get("events", [])

def add_event(
    event_type: str,
    title: str,
    description: str,
    details: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None
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
    timestamp = datetime.utcnow().isoformat()
    
    event = {
        "id": event_id,
        "event_type": event_type,
        "title": title,
        "description": description,
        "timestamp": timestamp,
        "status": status
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
    return event

# API endpoint to get all events
@router.get("/events")
async def get_timeline_events(
    current_user_or_service: Annotated[Union[User, str], Depends(get_current_user_or_service)],
    event_type: Optional[str] = None,
    limit: int = 100
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
    events = get_events()
    
    # Filter by event_type if provided
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]
    
    # Sort by timestamp (newest first)
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Limit the number of events
    return events[:limit]

# Function to log tool executions
def log_tool_execution(tool_name: str, parameters: Dict[str, Any], result: Dict[str, Any]) -> None:
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
        description = f"The tool '{tool_name}' is being executed with the provided parameters."
    else:
        title = f"Tool Executed: {tool_name}"
        description = f"The tool '{tool_name}' was executed with the provided parameters."
    
    add_event(
        event_type="tool_execution",
        title=title,
        description=description,
        details={
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result
        },
        status=status
    )

# Function to log system events
def log_system_event(title: str, description: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Log a system event to the timeline.
    
    Args:
        title: The title of the event
        description: A description of the event
        details: Optional additional details
    """
    add_event(
        event_type="system",
        title=title,
        description=description,
        details=details
    )

# Function to log errors
def log_error(title: str, description: str, details: Optional[Dict[str, Any]] = None) -> None:
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
        status="error"
    )