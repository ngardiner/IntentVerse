"""
Timeline Integration for MCP Proxy Engine.

This module provides timeline logging functionality for MCP proxy tool calls,
allowing tracking and monitoring of external tool executions.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProxyCallEvent:
    """Event data for a proxy tool call."""

    tool_name: str
    server_name: str
    original_name: str
    parameters: Dict[str, Any]
    start_time: float
    end_time: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    status: str = "pending"

    @property
    def duration_ms(self) -> Optional[float]:
        """Get call duration in milliseconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return None

    def to_timeline_event(self) -> Dict[str, Any]:
        """Convert to timeline event format."""
        # Determine event status
        if self.error:
            status = "error"
            title = f"Proxy Tool Failed: {self.tool_name}"
            description = f"Failed to execute '{self.original_name}' on server '{self.server_name}': {self.error}"
        elif self.end_time:
            status = "success"
            title = f"Proxy Tool Executed: {self.tool_name}"
            description = f"Successfully executed '{self.original_name}' on server '{self.server_name}'"
            if self.duration_ms:
                description += f" (took {self.duration_ms:.1f}ms)"
        else:
            status = "pending"
            title = f"Proxy Tool Executing: {self.tool_name}"
            description = (
                f"Executing '{self.original_name}' on server '{self.server_name}'"
            )

        # Create timeline event
        event = {
            "event_type": "mcp_proxy_call",
            "title": title,
            "description": description,
            "status": status,
            "details": {
                "tool_name": self.tool_name,
                "server_name": self.server_name,
                "original_name": self.original_name,
                "parameters": self.parameters,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_ms": self.duration_ms,
                "result": self.result if not self.error else None,
                "error": self.error,
                "proxy_type": "mcp_external_tool",
            },
        }

        return event


class ProxyTimelineLogger:
    """Timeline logger for MCP proxy tool calls."""

    def __init__(self):
        """Initialize the timeline logger."""
        self._timeline_module = None
        self._active_calls: Dict[str, ProxyCallEvent] = {}
        self._call_counter = 0

    def _get_timeline_module(self):
        """Get the timeline module (using Core API instead of direct imports)."""
        if self._timeline_module is None:
            try:
                # Use Core API for timeline logging instead of direct imports
                import httpx
                import os
                
                core_api_url = os.environ.get("CORE_API_URL", "http://localhost:8000")
                api_key = os.environ.get("SERVICE_API_KEY", "dev-service-key-12345")
                headers = {"X-API-Key": api_key}
                
                async def add_event_via_api(event_type, title, description, details=None, status="success"):
                    """Add event to timeline via Core API."""
                    try:
                        async with httpx.AsyncClient(base_url=core_api_url, headers=headers) as client:
                            payload = {
                                "tool_name": "timeline.add_event",
                                "parameters": {
                                    "event_type": event_type,
                                    "title": title,
                                    "description": description,
                                    "details": details or {},
                                    "status": status
                                }
                            }
                            response = await client.post("/api/v1/execute", json=payload)
                            response.raise_for_status()
                            return response.json()
                    except Exception as e:
                        logger.debug(f"Failed to log timeline event via API: {e}")
                        return None
                
                async def log_system_event_via_api(title, description, details=None):
                    """Log system event to timeline via Core API."""
                    return await add_event_via_api("system", title, description, details, "success")
                
                self._timeline_module = {
                    "add_event": add_event_via_api,
                    "log_system_event": log_system_event_via_api,
                }
                logger.debug("Timeline module configured to use Core API for MCP proxy logging")
            except Exception as e:
                logger.debug(f"Failed to configure timeline API client: {e}")
                # Create dummy functions to avoid errors
                self._timeline_module = {
                    "add_event": lambda *args, **kwargs: None,
                    "log_system_event": lambda *args, **kwargs: None,
                }
        return self._timeline_module

    def start_call(
        self,
        tool_name: str,
        server_name: str,
        original_name: str,
        parameters: Dict[str, Any],
    ) -> str:
        """
        Log the start of a proxy tool call.

        Args:
            tool_name: Name of the proxy tool
            server_name: Name of the MCP server
            original_name: Original name of the tool on the server
            parameters: Parameters passed to the tool

        Returns:
            Call ID for tracking this specific call
        """
        self._call_counter += 1
        call_id = f"proxy_call_{self._call_counter}_{int(time.time() * 1000)}"

        # Create call event
        call_event = ProxyCallEvent(
            tool_name=tool_name,
            server_name=server_name,
            original_name=original_name,
            parameters=parameters,
            start_time=time.time(),
            status="pending",
        )

        # Store active call
        self._active_calls[call_id] = call_event

        # Don't log to timeline yet - wait for call to complete
        logger.debug(f"Started proxy call tracking: {call_id} for {tool_name}")
        return call_id

    def end_call(
        self, call_id: str, result: Any = None, error: Optional[str] = None
    ) -> None:
        """
        Log the end of a proxy tool call.

        Args:
            call_id: Call ID returned from start_call
            result: Result of the tool call (if successful)
            error: Error message (if failed)
        """
        if call_id not in self._active_calls:
            logger.warning(f"Unknown call ID for end_call: {call_id}")
            return

        # Update call event
        call_event = self._active_calls[call_id]
        call_event.end_time = time.time()
        call_event.result = result
        call_event.error = error
        call_event.status = "error" if error else "success"

        # Log to timeline (async)
        timeline = self._get_timeline_module()
        if timeline:
            event_data = call_event.to_timeline_event()
            try:
                import asyncio
                # Run the async timeline logging in the background
                asyncio.create_task(timeline["add_event"](
                    event_type=event_data["event_type"],
                    title=event_data["title"],
                    description=event_data["description"],
                    details=event_data["details"],
                    status=event_data["status"],
                ))
            except Exception as e:
                logger.debug(f"Failed to create timeline logging task: {e}")

        # Remove from active calls
        del self._active_calls[call_id]

        logger.debug(f"Ended proxy call tracking: {call_id} for {call_event.tool_name}")

    def log_discovery_event(
        self,
        server_name: str,
        tools_discovered: int,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Log a tool discovery event.

        Args:
            server_name: Name of the MCP server
            tools_discovered: Number of tools discovered
            success: Whether discovery was successful
            error: Error message if discovery failed
        """
        timeline = self._get_timeline_module()
        if not timeline:
            return

        if success:
            title = f"MCP Server Discovery: {server_name}"
            description = f"Successfully discovered {tools_discovered} tools from MCP server '{server_name}'"
            status = "success"
        else:
            title = f"MCP Server Discovery Failed: {server_name}"
            description = f"Failed to discover tools from MCP server '{server_name}'"
            if error:
                description += f": {error}"
            status = "error"

        timeline["add_event"](
            event_type="mcp_discovery",
            title=title,
            description=description,
            details={
                "server_name": server_name,
                "tools_discovered": tools_discovered,
                "success": success,
                "error": error,
                "discovery_type": "mcp_server_tools",
            },
            status=status,
        )

        logger.debug(
            f"Logged discovery event for {server_name}: {tools_discovered} tools, success={success}"
        )

    def log_engine_event(
        self,
        event_type: str,
        title: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a general MCP proxy engine event.

        Args:
            event_type: Type of event (e.g., "startup", "shutdown", "error")
            title: Event title
            description: Event description
            details: Optional additional details
        """
        timeline = self._get_timeline_module()
        if not timeline:
            return

        # Determine status based on event type
        status = "success"
        if "error" in event_type.lower() or "fail" in event_type.lower():
            status = "error"
        elif "start" in event_type.lower() or "init" in event_type.lower():
            status = "pending"

        event_details = {
            "component": "mcp_proxy_engine",
            "event_type": event_type,
            **(details or {}),
        }

        timeline["add_event"](
            event_type="mcp_engine",
            title=title,
            description=description,
            details=event_details,
            status=status,
        )

        logger.debug(f"Logged engine event: {event_type} - {title}")

    def log_server_connection_event(
        self,
        server_name: str,
        event_type: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Log a server connection event.

        Args:
            server_name: Name of the MCP server
            event_type: Type of connection event (e.g., "connect", "disconnect", "reconnect")
            success: Whether the connection event was successful
            error: Error message if connection failed
        """
        timeline = self._get_timeline_module()
        if not timeline:
            return

        if success:
            title = f"MCP Server {event_type.title()}: {server_name}"
            description = f"Successfully {event_type}ed to MCP server '{server_name}'"
            status = "success"
        else:
            title = f"MCP Server {event_type.title()} Failed: {server_name}"
            description = f"Failed to {event_type} to MCP server '{server_name}'"
            if error:
                description += f": {error}"
            status = "error"

        timeline["add_event"](
            event_type="mcp_connection",
            title=title,
            description=description,
            details={
                "server_name": server_name,
                "connection_event": event_type,
                "success": success,
                "error": error,
            },
            status=status,
        )

        logger.debug(
            f"Logged connection event for {server_name}: {event_type}, success={success}"
        )

    def get_active_calls(self) -> Dict[str, ProxyCallEvent]:
        """Get currently active proxy calls."""
        return self._active_calls.copy()

    def get_call_stats(self) -> Dict[str, Any]:
        """Get statistics about proxy calls."""
        return {
            "active_calls": len(self._active_calls),
            "total_calls_started": self._call_counter,
            "active_call_ids": list(self._active_calls.keys()),
        }


# Global timeline logger instance
_timeline_logger: Optional[ProxyTimelineLogger] = None


def get_timeline_logger() -> ProxyTimelineLogger:
    """Get the global timeline logger instance."""
    global _timeline_logger
    if _timeline_logger is None:
        _timeline_logger = ProxyTimelineLogger()
    return _timeline_logger


def log_proxy_call_start(
    tool_name: str, server_name: str, original_name: str, parameters: Dict[str, Any]
) -> str:
    """
    Convenience function to log the start of a proxy tool call.

    Args:
        tool_name: Name of the proxy tool
        server_name: Name of the MCP server
        original_name: Original name of the tool on the server
        parameters: Parameters passed to the tool

    Returns:
        Call ID for tracking this specific call
    """
    return get_timeline_logger().start_call(
        tool_name, server_name, original_name, parameters
    )


def log_proxy_call_end(
    call_id: str, result: Any = None, error: Optional[str] = None
) -> None:
    """
    Convenience function to log the end of a proxy tool call.

    Args:
        call_id: Call ID returned from log_proxy_call_start
        result: Result of the tool call (if successful)
        error: Error message (if failed)
    """
    get_timeline_logger().end_call(call_id, result, error)


def log_discovery_event(
    server_name: str, tools_discovered: int, success: bool, error: Optional[str] = None
) -> None:
    """
    Convenience function to log a tool discovery event.

    Args:
        server_name: Name of the MCP server
        tools_discovered: Number of tools discovered
        success: Whether discovery was successful
        error: Error message if discovery failed
    """
    get_timeline_logger().log_discovery_event(
        server_name, tools_discovered, success, error
    )


def log_engine_event(
    event_type: str,
    title: str,
    description: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Convenience function to log a general MCP proxy engine event.

    Args:
        event_type: Type of event (e.g., "startup", "shutdown", "error")
        title: Event title
        description: Event description
        details: Optional additional details
    """
    get_timeline_logger().log_engine_event(event_type, title, description, details)


def log_server_connection_event(
    server_name: str, event_type: str, success: bool, error: Optional[str] = None
) -> None:
    """
    Convenience function to log a server connection event.

    Args:
        server_name: Name of the MCP server
        event_type: Type of connection event (e.g., "connect", "disconnect", "reconnect")
        success: Whether the connection event was successful
        error: Error message if connection failed
    """
    get_timeline_logger().log_server_connection_event(
        server_name, event_type, success, error
    )
