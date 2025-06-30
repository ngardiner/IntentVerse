"""
WebSocket connection manager for real-time updates.
"""

import logging
import json
from typing import Dict, List, Any, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages to connected clients.
    """

    def __init__(self):
        # Store active connections by channel
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.client_info: Dict[WebSocket, Dict[str, Any]] = {}
        logging.info("WebSocket connection manager initialized")

    async def connect(self, websocket: WebSocket, channel: str = "default"):
        """
        Connect a new WebSocket client to a specific channel.

        Args:
            websocket: The WebSocket connection
            channel: The channel to connect to (default: "default")
        """
        await websocket.accept()

        # Initialize the channel if it doesn't exist
        if channel not in self.active_connections:
            self.active_connections[channel] = set()

        # Add the connection to the channel
        self.active_connections[channel].add(websocket)

        # Store client info
        client_host = websocket.client.host if websocket.client else "unknown"
        connection_time = datetime.now().isoformat()
        self.client_info[websocket] = {
            "channel": channel,
            "client_host": client_host,
            "connected_at": connection_time,
        }

        logging.info(f"Client connected to channel '{channel}': {client_host}")

        # Send a welcome message
        await websocket.send_json(
            {
                "type": "connection_established",
                "channel": channel,
                "message": f"Connected to {channel} channel",
            }
        )

    def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket client.

        Args:
            websocket: The WebSocket connection to disconnect
        """
        # Find which channel this connection belongs to
        if websocket in self.client_info:
            channel = self.client_info[websocket]["channel"]
            client_host = self.client_info[websocket]["client_host"]

            # Remove from the channel
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)

                # If the channel is empty, remove it
                if not self.active_connections[channel]:
                    del self.active_connections[channel]

            # Remove client info
            del self.client_info[websocket]

            logging.info(f"Client disconnected from channel '{channel}': {client_host}")

    async def broadcast(self, message: Dict[str, Any], channel: str = "default"):
        """
        Broadcast a message to all connected clients in a channel.

        Args:
            message: The message to broadcast
            channel: The channel to broadcast to (default: "default")
        """
        if channel not in self.active_connections:
            logging.debug(f"No clients in channel '{channel}' to broadcast to")
            return

        disconnected_websockets = set()

        for websocket in self.active_connections[channel]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logging.error(f"Error broadcasting to client: {e}")
                disconnected_websockets.add(websocket)

        # Clean up any disconnected websockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket)

        logging.debug(
            f"Broadcast message to {len(self.active_connections[channel])} clients in channel '{channel}'"
        )

    async def send_personal_message(
        self, message: Dict[str, Any], websocket: WebSocket
    ):
        """
        Send a message to a specific client.

        Args:
            message: The message to send
            websocket: The WebSocket connection to send to
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logging.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    def get_channel_count(self, channel: str = "default") -> int:
        """
        Get the number of clients connected to a channel.

        Args:
            channel: The channel to count (default: "default")

        Returns:
            The number of clients connected to the channel
        """
        if channel not in self.active_connections:
            return 0
        return len(self.active_connections[channel])

    def get_total_connections(self) -> int:
        """
        Get the total number of connections across all channels.

        Returns:
            The total number of connections
        """
        return sum(len(connections) for connections in self.active_connections.values())


# Create a global instance of the connection manager
manager = ConnectionManager()
