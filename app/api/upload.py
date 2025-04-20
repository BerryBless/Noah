# ----------------------
# file   : app/api/upload.py
# function: 파일 업로드 API - ZIP 파일 + 썸네일 이미지 업로드 + 진행률 WebSocket 브로드캐스트 + 워커 큐 등록
# ----------------------

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
import os
from app.utils.logger import logger
import uuid
import shutil
from app.core.ws_manager import websocket_manager
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import app.core.background_worker as background_worker

router = APIRouter()

TEMP_DIR = "/data/temp"
MONGO_URI = os.getenv("MONGO_URI", "")

client = AsyncIOMotorClient(MONGO_URI)
db = client["noah_db"]
upload_queue = db["upload_queue"]

# ----------------------
# param   : files - 업로드할 파일 리스트
# param   : thumb - (선택) 썸네일 파일
# param   : upload_id - WebSocket ID
# function: 여러 파일을 임시 저장 → 상태 브로드캐스트 → 큐 등록
# return  : { "upload_id": string }
# ----------------------
@router.post("/upload")
async def upload_files_background(
    files: List[UploadFile] = File(...),
    thumb: Optional[UploadFile] = File(None),
    upload_id: Optional[str] = Form(None)
):
    try:
        if not upload_id:
            upload_id = str(uuid.uuid4())

        os.makedirs(TEMP_DIR, exist_ok=True)

        # ----------------------
        # 썸네일 저장 (옵션)
        # ----------------------
        thumb_path = ""
        if thumb:
            thumbs_dir = os.path.join(DATA_DIR, "thumbs")
            os.makedirs(thumbs_dir, exist_ok=True)
            thumb_path = os.path.join(thumbs_dir, f"{upload_id}_{thumb.filename}")
            with open(thumb_path, "wb") as f:
                shutil.copyfileobj(thumb.file, f)
            logger.info(f"[UPLOAD] 썸네일 저장 완료: {thumb_path}")

        # ----------------------
        # 파일 저장 및 큐 등록 (임시 저장 → 워커 처리)
        # ----------------------
        for file in files:
            temp_path = os.path.join(TEMP_DIR, f"{upload_id}_{file.filename}")
            with open(temp_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            logger.info(f"[UPLOAD] 파일 임시 저장 완료: {temp_path}")

            await websocket_manager.broadcast(upload_id, {
                "upload_id": upload_id,
                "file_name": file.filename,
                "status": "completed",
                "progress": 100
            })

            # DB 대기 등록
            await upload_queue.insert_one({
                "upload_id": upload_id,
                "file_name": file.filename,
                "temp_path": temp_path,
                "thumb_path": thumb_path,
                "status": "pending",
                "created_at": datetime.utcnow()
            })

            # 워커에 등록 (워커가 해시 계산 및 이동 수행)
            background_worker.enqueue(upload_id, file.filename, temp_path)

        return {"upload_id": upload_id}

    except Exception as e:
        logger.exception("[UPLOAD] 멀티 업로드 실패")
        raise HTTPException(status_code=500, detail="Upload failed")