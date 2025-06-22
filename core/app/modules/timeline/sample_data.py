"""
Sample data generator for the timeline module.
This is used to populate the timeline with sample events for testing and demonstration purposes.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from .tool import add_event

def generate_sample_events(count: int = 20) -> List[Dict[str, Any]]:
    """
    Generate sample timeline events.
    
    Args:
        count: Number of events to generate
        
    Returns:
        List of generated events
    """
    events = []
    
    # Event types and their probabilities
    event_types = [
        ("tool_execution", 0.7),  # 70% chance
        ("system", 0.2),          # 20% chance
        ("error", 0.1)            # 10% chance
    ]
    
    # Tool names for tool_execution events
    tool_names = [
        "filesystem.read_file",
        "filesystem.write_file",
        "filesystem.create_directory",
        "database.execute_query",
        "email.send_email",
        "web_search.search"
    ]
    
    # System event titles
    system_event_titles = [
        "MCP Interface Started",
        "MCP Interface Stopped",
        "Tool Registered",
        "Content Pack Loaded",
        "Database Connected",
        "Cache Cleared"
    ]
    
    # Error event titles
    error_event_titles = [
        "File Not Found",
        "Permission Denied",
        "Database Connection Failed",
        "Invalid Query",
        "Network Error",
        "Timeout"
    ]
    
    # Generate random events
    now = datetime.utcnow()
    
    for i in range(count):
        # Random timestamp within the last 24 hours
        timestamp = now - timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        # Choose event type based on probabilities
        event_type = random.choices(
            [et[0] for et in event_types],
            weights=[et[1] for et in event_types],
            k=1
        )[0]
        
        # Generate event based on type
        if event_type == "tool_execution":
            tool_name = random.choice(tool_names)
            title = f"Tool Executed: {tool_name}"
            description = f"The tool '{tool_name}' was executed with the provided parameters."
            
            # Generate random parameters based on tool name
            parameters = {}
            if "file" in tool_name:
                parameters["path"] = f"/documents/sample_{random.randint(1, 100)}.txt"
            if "write" in tool_name:
                parameters["content"] = "Sample content for the file."
            if "query" in tool_name:
                parameters["query"] = "SELECT * FROM users LIMIT 10"
            if "email" in tool_name:
                parameters["to"] = "user@example.com"
                parameters["subject"] = "Sample Email"
                parameters["body"] = "This is a sample email."
            if "search" in tool_name:
                parameters["query"] = "sample search query"
            
            # Random status
            status = random.choices(
                ["success", "error"],
                weights=[0.9, 0.1],  # 90% success, 10% error
                k=1
            )[0]
            
            # Add the event
            event = add_event(
                event_type=event_type,
                title=title,
                description=description,
                details={
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "result": {"status": status}
                },
                status=status
            )
            events.append(event)
            
        elif event_type == "system":
            title = random.choice(system_event_titles)
            
            if title == "MCP Interface Started":
                description = "The MCP Interface service has been started and is ready to accept connections."
            elif title == "MCP Interface Stopped":
                description = "The MCP Interface service has been stopped."
            elif title == "Tool Registered":
                tool_name = random.choice(tool_names)
                description = f"The tool '{tool_name}' has been registered with the MCP Interface."
            elif title == "Content Pack Loaded":
                description = "A content pack has been loaded."
            elif title == "Database Connected":
                description = "Successfully connected to the database."
            elif title == "Cache Cleared":
                description = "The cache has been cleared."
            
            # Add the event
            event = add_event(
                event_type=event_type,
                title=title,
                description=description
            )
            events.append(event)
            
        elif event_type == "error":
            title = random.choice(error_event_titles)
            
            if title == "File Not Found":
                description = f"The file '/documents/missing_{random.randint(1, 100)}.txt' was not found."
            elif title == "Permission Denied":
                description = "Permission denied when trying to access the file."
            elif title == "Database Connection Failed":
                description = "Failed to connect to the database. Connection timed out."
            elif title == "Invalid Query":
                description = "The SQL query contains syntax errors."
            elif title == "Network Error":
                description = "Failed to connect to the remote server."
            elif title == "Timeout":
                description = "The operation timed out after 30 seconds."
            
            # Add the event
            event = add_event(
                event_type=event_type,
                title=title,
                description=description,
                status="error"
            )
            events.append(event)
    
    return events