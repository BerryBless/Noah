# ----------------------
# file   : app/core/ws_manager.py
# function: WebSocket 연결 관리 및 메시지 브로드캐스트
# ----------------------
from typing import Dict, List
from fastapi import WebSocket
from asyncio import Lock

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
        self.lock = Lock()

    async def connect(self, upload_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.connections.setdefault(upload_id, []).append(websocket)

    async def disconnect(self, upload_id: str, websocket: WebSocket):
        async with self.lock:
            if upload_id in self.connections:
                self.connections[upload_id].remove(websocket)
                if not self.connections[upload_id]:
                    del self.connections[upload_id]

    async def broadcast(self, upload_id: str, message: dict):
        async with self.lock:
            conns = self.connections.get(upload_id, [])
        for conn in conns:
            await conn.send_json(message)

websocket_manager = WebSocketManager()