"""
WebSocket connection manager for real-time communication.
Handles client connections, message broadcasting, and room management.
"""

import json
import logging
import asyncio
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""
    # System messages
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    
    # Data messages
    SENSOR_DATA = "sensor_data"
    DEVICE_STATUS = "device_status"
    ALERT = "alert"
    SYSTEM_STATUS = "system_status"
    
    # Subscription messages
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    
    # Control messages
    COMMAND = "command"
    RESPONSE = "response"


class WebSocketMessage:
    """Structured WebSocket message."""
    
    def __init__(
        self,
        message_type: MessageType,
        data: Any = None,
        timestamp: Optional[datetime] = None,
        client_id: Optional[str] = None,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None
    ):
        self.message_type = message_type
        self.data = data
        self.timestamp = timestamp or datetime.utcnow()
        self.client_id = client_id
        self.farm_id = farm_id
        self.device_id = device_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        return {
            "type": self.message_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "client_id": self.client_id,
            "farm_id": self.farm_id,
            "device_id": self.device_id
        }
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class WebSocketClient:
    """WebSocket client connection wrapper."""
    
    def __init__(self, websocket: WebSocket, client_id: str, user_info: Optional[Dict[str, Any]] = None):
        self.websocket = websocket
        self.client_id = client_id
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.subscriptions: Set[str] = set()
        self.farm_ids: Set[str] = set()
        self.device_ids: Set[str] = set()
        self.user_info = user_info or {}
    
    async def send_message(self, message: WebSocketMessage):
        """Send message to client."""
        try:
            await self.websocket.send_text(message.to_json())
            logger.debug(f"Sent message to client {self.client_id}: {message.message_type}")
        except Exception as e:
            logger.error(f"Failed to send message to client {self.client_id}: {e}")
            raise
    
    async def send_error(self, error_message: str, error_code: str = "GENERAL_ERROR"):
        """Send error message to client."""
        error_data = {
            "code": error_code,
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        message = WebSocketMessage(MessageType.ERROR, data=error_data, client_id=self.client_id)
        await self.send_message(message)
    
    def add_subscription(self, subscription: str):
        """Add subscription filter."""
        self.subscriptions.add(subscription)
        logger.debug(f"Client {self.client_id} subscribed to: {subscription}")
    
    def remove_subscription(self, subscription: str):
        """Remove subscription filter."""
        self.subscriptions.discard(subscription)
        logger.debug(f"Client {self.client_id} unsubscribed from: {subscription}")
    
    def update_heartbeat(self):
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        # Active connections
        self.active_connections: Dict[str, WebSocketClient] = {}
        
        # Room-based grouping
        self.farm_rooms: Dict[str, Set[str]] = {}  # farm_id -> client_ids
        self.device_rooms: Dict[str, Set[str]] = {}  # device_id -> client_ids
        
        # Message queue for offline delivery (optional)
        self.message_queue: Dict[str, List[WebSocketMessage]] = {}
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "errors": 0
        }
    
    async def connect(self, websocket: WebSocket, client_id: str, user_info: Optional[Dict[str, Any]] = None) -> WebSocketClient:
        """Accept WebSocket connection and register client."""
        try:
            await websocket.accept()
            
            client = WebSocketClient(websocket, client_id, user_info)
            self.active_connections[client_id] = client
            
            # Update statistics
            self.stats["total_connections"] += 1
            self.stats["active_connections"] = len(self.active_connections)
            
            # Send welcome message
            welcome_message = WebSocketMessage(
                MessageType.CONNECT,
                data={
                    "client_id": client_id,
                    "server_time": datetime.utcnow().isoformat(),
                    "supported_message_types": [t.value for t in MessageType]
                },
                client_id=client_id
            )
            await client.send_message(welcome_message)
            
            logger.info(f"WebSocket client connected: {client_id}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket client {client_id}: {e}")
            self.stats["errors"] += 1
            raise
    
    async def disconnect(self, client_id: str):
        """Disconnect client and cleanup resources."""
        try:
            if client_id in self.active_connections:
                client = self.active_connections[client_id]
                
                # Remove from rooms
                for farm_id in client.farm_ids:
                    if farm_id in self.farm_rooms:
                        self.farm_rooms[farm_id].discard(client_id)
                        if not self.farm_rooms[farm_id]:
                            del self.farm_rooms[farm_id]
                
                for device_id in client.device_ids:
                    if device_id in self.device_rooms:
                        self.device_rooms[device_id].discard(client_id)
                        if not self.device_rooms[device_id]:
                            del self.device_rooms[device_id]
                
                # Remove client
                del self.active_connections[client_id]
                
                # Update statistics
                self.stats["active_connections"] = len(self.active_connections)
                
                logger.info(f"WebSocket client disconnected: {client_id}")
                
        except Exception as e:
            logger.error(f"Error during client disconnect {client_id}: {e}")
    
    async def send_to_client(self, client_id: str, message: WebSocketMessage):
        """Send message to specific client."""
        try:
            if client_id in self.active_connections:
                client = self.active_connections[client_id]
                await client.send_message(message)
                self.stats["messages_sent"] += 1
            else:
                logger.warning(f"Attempted to send message to non-existent client: {client_id}")
                
        except WebSocketDisconnect:
            await self.disconnect(client_id)
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            self.stats["errors"] += 1
    
    async def broadcast_to_farm(self, farm_id: str, message: WebSocketMessage):
        """Broadcast message to all clients subscribed to a farm."""
        try:
            if farm_id in self.farm_rooms:
                client_ids = list(self.farm_rooms[farm_id])
                await self.broadcast_to_clients(client_ids, message)
                logger.debug(f"Broadcasted message to farm {farm_id}: {len(client_ids)} clients")
                
        except Exception as e:
            logger.error(f"Failed to broadcast to farm {farm_id}: {e}")
            self.stats["errors"] += 1
    
    async def broadcast_to_device(self, device_id: str, message: WebSocketMessage):
        """Broadcast message to all clients subscribed to a device."""
        try:
            if device_id in self.device_rooms:
                client_ids = list(self.device_rooms[device_id])
                await self.broadcast_to_clients(client_ids, message)
                logger.debug(f"Broadcasted message to device {device_id}: {len(client_ids)} clients")
                
        except Exception as e:
            logger.error(f"Failed to broadcast to device {device_id}: {e}")
            self.stats["errors"] += 1
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all connected clients."""
        try:
            client_ids = list(self.active_connections.keys())
            await self.broadcast_to_clients(client_ids, message)
            logger.debug(f"Broadcasted message to all clients: {len(client_ids)} clients")
            
        except Exception as e:
            logger.error(f"Failed to broadcast to all clients: {e}")
            self.stats["errors"] += 1
    
    async def broadcast_to_clients(self, client_ids: List[str], message: WebSocketMessage):
        """Broadcast message to specific list of clients."""
        tasks = []
        for client_id in client_ids:
            if client_id in self.active_connections:
                tasks.append(self.send_to_client(client_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def handle_subscription(self, client_id: str, subscription_data: Dict[str, Any]):
        """Handle client subscription to farms/devices."""
        try:
            if client_id not in self.active_connections:
                return
            
            client = self.active_connections[client_id]
            
            # Handle farm subscriptions
            if "farm_ids" in subscription_data:
                for farm_id in subscription_data["farm_ids"]:
                    if farm_id not in self.farm_rooms:
                        self.farm_rooms[farm_id] = set()
                    self.farm_rooms[farm_id].add(client_id)
                    client.farm_ids.add(farm_id)
            
            # Handle device subscriptions
            if "device_ids" in subscription_data:
                for device_id in subscription_data["device_ids"]:
                    if device_id not in self.device_rooms:
                        self.device_rooms[device_id] = set()
                    self.device_rooms[device_id].add(client_id)
                    client.device_ids.add(device_id)
            
            # Handle general subscriptions
            if "message_types" in subscription_data:
                for msg_type in subscription_data["message_types"]:
                    client.add_subscription(msg_type)
            
            logger.info(f"Updated subscriptions for client {client_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle subscription for client {client_id}: {e}")
    
    async def process_client_message(self, client_id: str, message_data: Dict[str, Any]):
        """Process incoming message from client."""
        try:
            if client_id not in self.active_connections:
                return
            
            client = self.active_connections[client_id]
            message_type = message_data.get("type")
            
            if message_type == MessageType.HEARTBEAT:
                client.update_heartbeat()
                # Send heartbeat response
                response = WebSocketMessage(
                    MessageType.HEARTBEAT,
                    data={"status": "alive", "server_time": datetime.utcnow().isoformat()},
                    client_id=client_id
                )
                await client.send_message(response)
                
            elif message_type == MessageType.SUBSCRIBE:
                await self.handle_subscription(client_id, message_data.get("data", {}))
                
            elif message_type == MessageType.UNSUBSCRIBE:
                # Handle unsubscription logic
                pass
                
            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")
                
        except Exception as e:
            logger.error(f"Failed to process message from client {client_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            **self.stats,
            "farm_rooms": len(self.farm_rooms),
            "device_rooms": len(self.device_rooms),
            "uptime": (datetime.utcnow() - datetime.utcnow()).total_seconds()  # Will be updated with actual start time
        }
    
    async def cleanup_stale_connections(self, max_idle_seconds: int = 300):
        """Remove stale connections that haven't sent heartbeat."""
        try:
            current_time = datetime.utcnow()
            stale_clients = []
            
            for client_id, client in self.active_connections.items():
                idle_seconds = (current_time - client.last_heartbeat).total_seconds()
                if idle_seconds > max_idle_seconds:
                    stale_clients.append(client_id)
            
            for client_id in stale_clients:
                logger.warning(f"Removing stale WebSocket connection: {client_id}")
                await self.disconnect(client_id)
                
        except Exception as e:
            logger.error(f"Error during stale connection cleanup: {e}")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()