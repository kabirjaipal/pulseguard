import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket
from redis.asyncio import Redis
from app.core.config import settings

class ConnectionManager:
    def __init__(self):
        # Maps user_id (int) -> list of active WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept connection and register it under the user's ID."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"WebSocket client connected. User ID: {user_id}. Active connections: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Unregister the connection when client disconnects."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"WebSocket client disconnected. User ID: {user_id}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a JSON payload to a specific connection."""
        await websocket.send_json(message)

    async def broadcast_to_user(self, user_id: int, message: dict):
        """Send a JSON payload to all active connections owned by a specific user."""
        if user_id in self.active_connections:
            # Create a copy of the list to avoid mutation issues during iteration
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to WebSocket for User {user_id}: {str(e)}")
                    self.disconnect(connection, user_id)

# Global connection manager instance
manager = ConnectionManager()

async def redis_pubsub_listener():
    """
    Subscribes to the 'pulseguard_updates' Redis channel and broadcasts
    messages to the appropriate WebSocket clients.
    """
    print("Starting Redis Pub/Sub WebSocket broadcast listener...")
    async_redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = async_redis.pubsub()
    await pubsub.subscribe("pulseguard_updates")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    owner_id = payload.get("owner_id")
                    if owner_id:
                        await manager.broadcast_to_user(int(owner_id), payload)
                except Exception as json_err:
                    print(f"Error parsing Redis Pub/Sub message data: {str(json_err)}")
    except asyncio.CancelledError:
        print("Redis Pub/Sub listener task cancelled.")
    except Exception as e:
        print(f"Error in Redis Pub/Sub listener: {str(e)}")
    finally:
        await pubsub.unsubscribe("pulseguard_updates")
        await async_redis.close()
