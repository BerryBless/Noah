# ----------------------
# file   : app/api/ws_upload.py
# function: WebSocket으로 업로드 진행률 브로드캐스트
# ----------------------
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import websocket_manager

router = APIRouter()

@router.websocket("/ws/upload-progress/{upload_id}")
async def upload_progress_ws(websocket: WebSocket, upload_id: str):
    await websocket_manager.connect(upload_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # 클라이언트 heartbeat 또는 keep-alive
    except WebSocketDisconnect:
        await websocket_manager.disconnect(upload_id, websocket)
