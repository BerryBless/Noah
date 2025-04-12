# ----------------------
# file   : app/api/upload.py
# function: 파일 업로드 API - ZIP 파일 + 썸네일 이미지 업로드 + 진행률 WebSocket 브로드캐스트 + 워커 큐 등록
# ----------------------

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
import os
import logging
import uuid
import shutil
from app.services.worker_pool import get_worker_pool
from app.services.tag_manager import split_tags
from app.core.ws_manager import websocket_manager
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from app.core import background_worker

router = APIRouter()
logger = logging.getLogger(__name__)

TEMP_DIR = "/data/temp"

client = AsyncIOMotorClient("mongodb://host.docker.internal:27017")
db = client["noah_db"]
upload_queue = db["upload_queue"]

# ----------------------
# param   : file - 업로드된 ZIP 파일
# param   : thumb - 썸네일 이미지 (선택 사항)
# param   : tags - 태그 문자열 리스트 (FormData로 전달)
# param   : upload_id - 실시간 진행률 전송용 ID
# function: ZIP과 썸네일을 임시 저장하며 WebSocket으로 진행률 전송, 이후 워커에 경로 전달
# return  : 저장 완료 메시지
# ----------------------
@router.post("/upload-once")
async def upload_file(
    file: UploadFile = File(...),
    thumb: Optional[UploadFile] = File(None),
    tags: Optional[List[str]] = Form(default=[]),
    upload_id: Optional[str] = Form(None)
):
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_path = os.path.join(TEMP_DIR, file.filename)

    try:
        # ----------------------
        # ZIP 파일 저장 with 진행률 전송
        # ----------------------
        chunk_size = 1024 * 1024  # 1MB
        total = 0

        with open(temp_path, "wb") as buffer:
            while chunk := file.file.read(chunk_size):
                buffer.write(chunk)
                total += len(chunk)

                # WebSocket 브로드캐스트
                if upload_id:
                    await websocket_manager.broadcast(upload_id, {
                        "upload_id": upload_id,
                        "status": "uploading",
                        "progress": min(100, int(total / (20 * chunk_size) * 100))
                    })

        if upload_id:
            await websocket_manager.broadcast(upload_id, {
                "upload_id": upload_id,
                "status": "completed",
                "progress": 100
            })

        logger.info(f"[UPLOAD] 임시 저장 완료: {temp_path}")

        # ----------------------
        # 썸네일 이미지 저장 (선택적)
        # ----------------------
        thumb_path = ""
        if thumb:
            thumbs_dir = os.path.join("/data", "thumbs")
            os.makedirs(thumbs_dir, exist_ok=True)

            base_name = os.path.splitext(file.filename)[0]
            thumb_ext = os.path.splitext(thumb.filename)[1]
            thumb_save_name = f"{base_name}_thumb{thumb_ext}"

            saved_thumb_path = os.path.join(thumbs_dir, thumb_save_name)
            with open(saved_thumb_path, "wb") as buffer:
                buffer.write(thumb.file.read())
            logger.info(f"[UPLOAD] 썸네일 저장 완료: {saved_thumb_path}")

            thumb_path = f"/thumbs/{thumb_save_name}"

        # ----------------------
        # 태그 문자열 전처리
        # ----------------------
        cleaned_tags = split_tags(tags)

        # ----------------------
        # 워커 스레드 풀에 작업 등록
        # ----------------------
        worker_pool = get_worker_pool()
        if worker_pool is not None:
            worker_pool.add_task(temp_path, cleaned_tags, thumb_path)
        else:
            logging.error("[UPLOAD] get_worker_pool() → None입니다. 워커가 등록되지 않았습니다.")
            raise RuntimeError("WorkerPool이 초기화되지 않았습니다.")

        return {"message": f"{file.filename} 업로드 완료"}

    except Exception as e:
        logger.exception(f"[UPLOAD] 업로드 실패: {e}")
        if upload_id:
            await websocket_manager.broadcast(upload_id, {
                "upload_id": upload_id,
                "status": "failed",
                "progress": 0
            })
        raise HTTPException(status_code=500, detail="파일 저장 중 오류 발생")
    
# ----------------------
# param   : file - 업로드할 메인 파일
# param   : thumb - (선택) 썸네일 파일
# function: 파일 업로드 요청 처리 → 임시 저장 후 큐에 등록
# return  : { "upload_id": string }
# ----------------------
@router.post("/upload")
async def upload_file_background(
    file: UploadFile = File(...),
    thumb: Optional[UploadFile] = File(None)
):
    try:
        # 1. 고유 업로드 ID 생성
        upload_id = str(uuid.uuid4())

        # 2. 임시 디렉토리 준비
        temp_dir = os.path.join("/data/temp")
        os.makedirs(temp_dir, exist_ok=True)

        # 3. 업로드된 파일을 임시 저장
        temp_path = os.path.join(temp_dir, f"{upload_id}_{file.filename}")
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 4. 썸네일 저장 (옵션)
        thumb_path = ""
        if thumb:
            thumbs_dir = os.path.join("/data", "thumbs")
            os.makedirs(thumbs_dir, exist_ok=True)
            thumb_name = f"{upload_id}_{thumb.filename}"
            saved_thumb_path = os.path.join(thumbs_dir, thumb_name)
            with open(saved_thumb_path, "wb") as buffer:
                shutil.copyfileobj(thumb.file, buffer)
            thumb_path = f"/thumbs/{thumb_name}"

        # 5. 업로드 큐에 초기 정보 기록
        await upload_queue.insert_one({
            "upload_id": upload_id,
            "file_name": file.filename,
            "thumb_path": thumb_path,
            "status": "pending",
            "created_at": datetime.utcnow()
        })

        # 6. 워커에 업로드 작업 enqueue
        background_worker.enqueue(upload_id, temp_path)

        # 7. 즉시 응답
        return {"upload_id": upload_id}

    except Exception as e:
        logger.exception("[UPLOAD] 업로드 실패")
        raise HTTPException(status_code=500, detail="Upload failed.")