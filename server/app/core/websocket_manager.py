import asyncio
import json
import logging
from typing import Dict, List
from fastapi import WebSocket
from redis.asyncio import Redis
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

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
        logger.info("WebSocket client connected. User ID: %d. Active connections: %d", user_id, len(self.active_connections[user_id]))

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Unregister the connection when client disconnects."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info("WebSocket client disconnected. User ID: %d", user_id)

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
                    logger.error("Error broadcasting to WebSocket for User %d: %s", user_id, str(e), exc_info=True)
                    self.disconnect(connection, user_id)

# Global connection manager instance
manager = ConnectionManager()

async def redis_pubsub_listener():
    """
    Subscribes to the 'pulseguard_updates' Redis channel and broadcasts
    messages to the appropriate WebSocket clients.
    Automatically reconnects on connection errors or timeouts.
    """
    logger.info("Starting Redis Pub/Sub WebSocket broadcast listener...")
    while True:
        pubsub = None
        async_redis = None
        try:
            from app.core.redis_client import redis_available, InMemoryRedis
            
            if redis_available:
                # Set socket_timeout=None to block indefinitely and health_check_interval to keep connection alive
                async_redis = Redis.from_url(
                    settings.REDIS_URL, 
                    decode_responses=True, 
                    socket_timeout=None, 
                    health_check_interval=30
                )
            else:
                async_redis = InMemoryRedis()
                
            pubsub = async_redis.pubsub()
            await pubsub.subscribe("pulseguard_updates")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        payload = json.loads(message["data"])
                        owner_id = payload.get("owner_id")
                        if owner_id:
                            await manager.broadcast_to_user(int(owner_id), payload)
                    except Exception as json_err:
                        logger.error("Error parsing Redis Pub/Sub message data: %s", str(json_err), exc_info=True)
        except asyncio.CancelledError:
            logger.info("Redis Pub/Sub listener task cancelled.")
            break
        except (redis.exceptions.TimeoutError, asyncio.TimeoutError):
            # Quietly reconnect on read timeouts without printing traceback
            logger.debug("Redis Pub/Sub listener read timeout. Reconnecting...")
            continue
        except Exception as e:
            logger.error("Error in Redis Pub/Sub listener: %s. Reconnecting in 5 seconds...", str(e), exc_info=True)
            await asyncio.sleep(5)
        finally:
            try:
                if pubsub:
                    await pubsub.unsubscribe("pulseguard_updates")
                if async_redis:
                    await async_redis.close()
            except Exception:
                pass

