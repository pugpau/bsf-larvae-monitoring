"""
WebSocket API routes for real-time communication.
Provides WebSocket endpoints for live data streaming and notifications.
"""

import json
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query, status
from datetime import datetime
from jose import JWTError, jwt

from src.websocket.manager import websocket_manager, WebSocketMessage, MessageType
from src.utils.logging import get_logger
from src.auth.security import SecurityConfig
from src.auth.repository import UserRepository
from src.database.postgresql import get_async_session

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


def generate_client_id() -> str:
    """Generate unique client ID."""
    return f"client_{uuid.uuid4().hex[:8]}"


async def get_user_from_token(token: Optional[str]):
    """Verify WebSocket authentication token."""
    if not token:
        return None
    
    # Development mode: Allow demo token
    if token == "demo-token":
        # Return mock user for development
        from src.auth.models import User, UserRole
        return User(
            id=uuid.uuid4(),
            username="demo",
            email="demo@example.com",
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=True,
            permissions=["VIEW_ANALYTICS", "MANAGE_ANALYTICS", "VIEW_SENSORS", "MANAGE_SENSORS"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, 
            SecurityConfig.SECRET_KEY, 
            algorithms=[SecurityConfig.ALGORITHM]
        )
        user_id = payload.get("sub")
        
        if user_id is None:
            return None
        
        # Get user from database
        async for session in get_async_session():
            user_repo = UserRepository(session)
            user = await user_repo.get_user_by_id(user_id)
            return user
            
    except JWTError:
        return None
    except Exception as e:
        logger.error(f"Error verifying WebSocket token: {e}")
        return None


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket, 
    client_id: Optional[str] = None,
    token: Optional[str] = Query(None)
):
    """
    Main WebSocket endpoint for real-time communication.
    
    Supports:
    - Real-time sensor data streaming
    - Live alerts and notifications
    - System status updates
    - Device status monitoring
    
    Authentication:
    - Token should be passed as query parameter: ws://host/ws/connect?token=<jwt_token>
    """
    if not client_id:
        client_id = generate_client_id()
    
    # Authenticate user
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    client = None
    try:
        # Accept connection and register client with user info
        client = await websocket_manager.connect(websocket, client_id, user_info={
            "user_id": str(user.id),
            "username": user.username,
            "role": user.role,
            "permissions": user.permissions
        })
        
        logger.info(f"WebSocket client {client_id} connected for user {user.username}")
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Process client message
                await websocket_manager.process_client_message(client_id, message_data)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client {client_id} disconnected normally")
                break
                
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from client {client_id}: {e}")
                if client:
                    await client.send_error("Invalid JSON format", "JSON_DECODE_ERROR")
                
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}")
                if client:
                    await client.send_error(f"Message processing error: {str(e)}", "MESSAGE_PROCESSING_ERROR")
    
    except Exception as e:
        logger.error(f"WebSocket connection error for client {client_id}: {e}")
        
    finally:
        # Clean up on disconnect
        await websocket_manager.disconnect(client_id)


@router.websocket("/farm/{farm_id}")
async def farm_websocket_endpoint(
    websocket: WebSocket, 
    farm_id: str, 
    client_id: Optional[str] = None,
    token: Optional[str] = Query(None)
):
    """
    Farm-specific WebSocket endpoint.
    Automatically subscribes to farm-specific data streams.
    """
    if not client_id:
        client_id = generate_client_id()
    
    # Authenticate user
    user = await get_user_from_token(token)
    if not user:
        logger.warning(f"Farm WebSocket authentication failed for client {client_id}, farm {farm_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    # TODO: Check if user has access to this farm
    # For now, we'll allow all authenticated users
    
    try:
        # Accept connection and register client
        client = await websocket_manager.connect(websocket, client_id, user_info={
            "user_id": str(user.id),
            "username": user.username,
            "role": user.role,
            "permissions": user.permissions,
            "farm_id": farm_id
        })
        
        # Auto-subscribe to farm
        await websocket_manager.handle_subscription(client_id, {
            "farm_ids": [farm_id],
            "message_types": [
                MessageType.SENSOR_DATA,
                MessageType.DEVICE_STATUS,
                MessageType.ALERT,
                MessageType.SYSTEM_STATUS
            ]
        })
        
        logger.info(f"WebSocket client {client_id} connected to farm {farm_id} for user {user.username}")
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                await websocket_manager.process_client_message(client_id, message_data)
                
            except WebSocketDisconnect:
                logger.info(f"Farm WebSocket client {client_id} disconnected")
                break
                
            except Exception as e:
                logger.error(f"Error in farm WebSocket for client {client_id}: {e}")
                if client:
                    await client.send_error(f"Error: {str(e)}", "FARM_WEBSOCKET_ERROR")
    
    finally:
        await websocket_manager.disconnect(client_id)


@router.websocket("/device/{device_id}")
async def device_websocket_endpoint(
    websocket: WebSocket, 
    device_id: str, 
    client_id: Optional[str] = None,
    token: Optional[str] = Query(None)
):
    """
    Device-specific WebSocket endpoint.
    Automatically subscribes to device-specific data streams.
    """
    if not client_id:
        client_id = generate_client_id()
    
    # Authenticate user
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    # TODO: Check if user has access to this device
    # For now, we'll allow all authenticated users
    
    try:
        # Accept connection and register client
        client = await websocket_manager.connect(websocket, client_id, user_info={
            "user_id": str(user.id),
            "username": user.username,
            "role": user.role,
            "permissions": user.permissions,
            "device_id": device_id
        })
        
        # Auto-subscribe to device
        await websocket_manager.handle_subscription(client_id, {
            "device_ids": [device_id],
            "message_types": [
                MessageType.SENSOR_DATA,
                MessageType.DEVICE_STATUS,
                MessageType.ALERT
            ]
        })
        
        logger.info(f"WebSocket client {client_id} connected to device {device_id} for user {user.username}")
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                await websocket_manager.process_client_message(client_id, message_data)
                
            except WebSocketDisconnect:
                logger.info(f"Device WebSocket client {client_id} disconnected")
                break
                
            except Exception as e:
                logger.error(f"Error in device WebSocket for client {client_id}: {e}")
                if client:
                    await client.send_error(f"Error: {str(e)}", "DEVICE_WEBSOCKET_ERROR")
    
    finally:
        await websocket_manager.disconnect(client_id)


# REST endpoints for WebSocket management

@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    try:
        stats = websocket_manager.get_stats()
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve WebSocket statistics")


@router.post("/broadcast")
async def broadcast_message(
    message_type: str,
    data: Dict[str, Any],
    farm_id: Optional[str] = None,
    device_id: Optional[str] = None
):
    """
    Broadcast message to WebSocket clients.
    
    Args:
        message_type: Type of message to send
        data: Message payload
        farm_id: Optional farm ID to target specific farm
        device_id: Optional device ID to target specific device
    """
    try:
        # Validate message type
        try:
            msg_type = MessageType(message_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid message type: {message_type}")
        
        # Create message
        message = WebSocketMessage(
            message_type=msg_type,
            data=data,
            farm_id=farm_id,
            device_id=device_id
        )
        
        # Broadcast message
        if farm_id:
            await websocket_manager.broadcast_to_farm(farm_id, message)
            target = f"farm {farm_id}"
        elif device_id:
            await websocket_manager.broadcast_to_device(device_id, message)
            target = f"device {device_id}"
        else:
            await websocket_manager.broadcast_to_all(message)
            target = "all clients"
        
        logger.info(f"Broadcasted {message_type} message to {target}")
        
        return {
            "status": "success",
            "message": f"Message broadcasted to {target}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to broadcast message: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast message")


@router.post("/cleanup")
async def cleanup_stale_connections(max_idle_seconds: int = 300):
    """Clean up stale WebSocket connections."""
    try:
        await websocket_manager.cleanup_stale_connections(max_idle_seconds)
        
        return {
            "status": "success",
            "message": "Stale connections cleaned up",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup stale connections: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup stale connections")