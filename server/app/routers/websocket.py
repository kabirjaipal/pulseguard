from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import InvalidTokenError
import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.core.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSockets"])

def get_user_from_token(db: Session, token: str) -> User | None:
    """Helper to decode and validate JWT token and retrieve user."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
        return db.query(User).filter(User.email == email).first()
    except InvalidTokenError:
        return None
    except Exception:
        return None

@router.websocket("/api/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None)
):
    """
    WebSocket endpoint for real-time endpoint status updates.
    Expects JWT token as a query parameter: ws://localhost:8000/api/ws?token=JWT_TOKEN
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token.")
        return

    db = SessionLocal()
    try:
        # 1. Authenticate user from JWT token
        user = get_user_from_token(db, token)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token.")
            return

        # 2. Register connection
        await manager.connect(websocket, user.id)

        # 3. Maintain connection alive
        try:
            while True:
                # Keep connection alive, listen for any messages from client
                # Client doesn't need to send messages, but if they do, we log or echo
                data = await websocket.receive_text()
                # Respond to simple pings
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            manager.disconnect(websocket, user.id)
            
    except Exception as e:
        logger.error("Error in websocket endpoint: %s", str(e), exc_info=True)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
    finally:
        db.close()

