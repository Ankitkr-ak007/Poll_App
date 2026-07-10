from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        # poll_id -> list of active connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, poll_id: str):
        await websocket.accept()
        if poll_id not in self.active_connections:
            self.active_connections[poll_id] = []
        self.active_connections[poll_id].append(websocket)

    def disconnect(self, websocket: WebSocket, poll_id: str):
        if poll_id in self.active_connections:
            if websocket in self.active_connections[poll_id]:
                self.active_connections[poll_id].remove(websocket)
            if not self.active_connections[poll_id]:
                del self.active_connections[poll_id]

    async def broadcast_poll_results(self, poll_id: str, results: dict):
        if poll_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[poll_id]:
                try:
                    await connection.send_text(json.dumps(results))
                except Exception:
                    disconnected.append(connection)
            
            # Clean up dead connections
            for d in disconnected:
                self.active_connections[poll_id].remove(d)

manager = ConnectionManager()
