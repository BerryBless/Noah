# ----------------------
# file   : app/api/upload.py
# function: 파일 업로드 API - ZIP 파일 + 썸네일 이미지 업로드 + 진행률 WebSocket 브로드캐스트 + 워커 큐 등록
# ----------------------

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
import os
import logging

from app.services.worker_pool import get_worker_pool
from app.services.tag_manager import split_tags
from app.core.ws_manager import websocket_manager

router = APIRouter()
logger = logging.getLogger(__name__)

TEMP_DIR = "/data/temp"

# ----------------------
# param   : file - 업로드된 ZIP 파일
# param   : thumb - 썸네일 이미지 (선택 사항)
# param   : tags - 태그 문자열 리스트 (FormData로 전달)
# param   : upload_id - 실시간 진행률 전송용 ID
# function: ZIP과 썸네일을 임시 저장하며 WebSocket으로 진행률 전송, 이후 워커에 경로 전달
# return  : 저장 완료 메시지
# ----------------------
@router.post("/upload")
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