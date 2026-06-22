from fastapi import WebSocket
from typing import List, Dict, Any
import logging

logger = logging.getLogger("websocket_manager")
logger.setLevel(logging.INFO)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, event_name: str, data: Dict[str, Any]):
        """
        Broadcasts a JSON payload to all active WebSocket connections.
        """
        message = {
            "event": event_name,
            "data": data
        }
        logger.info(f"Broadcasting event '{event_name}' to {len(self.active_connections)} clients.")
        
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send JSON to active connection, marking for removal: {e}")
                disconnected_clients.append(connection)
                
        for conn in disconnected_clients:
            self.disconnect(conn)

manager = ConnectionManager()
