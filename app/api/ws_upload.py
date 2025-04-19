# ----------------------
# file   : app/api/ws_upload.py
# function: WebSocket을 통해 업로드 상태를 실시간 전송
# ----------------------

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import json

MONGO_URI = os.getenv("MONGO_URI", "")
router = APIRouter()
client = AsyncIOMotorClient(MONGO_URI)
db = client["noah_db"]
upload_queue = db["upload_queue"]

# ----------------------
# param   : websocket - 클라이언트 WebSocket 연결 객체
# param   : upload_id - 업로드 식별 ID
# function: 주기적으로 업로드 상태를 조회하고 클라이언트에 전송
# return  : 연결 종료 시 자동 종료
# ----------------------
@router.websocket("/ws/upload/{upload_id}")
async def websocket_upload_status(websocket: WebSocket, upload_id: str):
    await websocket.accept()

    try:
        while True:
            # 상태 조회
            doc = await upload_queue.find_one({"upload_id": upload_id})
            if doc is None:
                await websocket.send_json({"status": "not_found"})
                break

            status = doc.get("status", "unknown")
            await websocket.send_json({"status": status})

            # 완료 상태면 연결 종료
            if status in ["completed", "failed", "duplicate"]:
                break

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        print(f"[WS] 클라이언트 연결 종료: {upload_id}")

    except Exception as e:
        await websocket.send_json({"status": "error", "detail": str(e)})
        await websocket.close()
