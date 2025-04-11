# ----------------------
# file   : app/api/upload.py
# function: 파일 업로드 API - ZIP 파일 + 썸네일 이미지 업로드 지원
# ----------------------

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
import os
import shutil
import logging

from app.services.worker_pool import get_worker_pool
from app.services.tag_manager import split_tags

router = APIRouter()
logger = logging.getLogger(__name__)

TEMP_DIR = "/data/temp"

# ----------------------
# param   : file - 업로드된 ZIP 파일
# param   : thumb - 썸네일 이미지 (선택 사항)
# param   : tags - 태그 문자열 리스트 (FormData로 전달)
# function: ZIP과 썸네일을 임시 저장 후 워커에 경로 전달
# return  : 저장 완료 메시지
# ----------------------
@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    thumb: Optional[UploadFile] = File(None),
    tags: Optional[List[str]] = Form(default=[])
):
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_path = os.path.join(TEMP_DIR, file.filename)

    try:
        # ----------------------
        # ZIP 파일 저장
        # ----------------------
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"[UPLOAD] 임시 저장 완료: {temp_path}")

        # ----------------------
        # 썸네일 이미지 저장 (선택적)
        # ----------------------
        thumb_path = ""
        if thumb:
            thumbs_dir = os.path.join("/data", "thumbs")
            os.makedirs(thumbs_dir, exist_ok=True)
            saved_thumb_path = os.path.join(thumbs_dir, thumb.filename)
            with open(saved_thumb_path, "wb") as buffer:
                shutil.copyfileobj(thumb.file, buffer)
            logger.info(f"[UPLOAD] 썸네일 저장 완료: {saved_thumb_path}")

            # 클라이언트 접근 경로 기준으로 저장
            thumb_path = f"/thumbs/{thumb.filename}"

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
            raise RuntimeError("WorkerPool이 초기화되지 않았습니다.")

        return {"message": f"{file.filename} 업로드 완료"}

    except Exception as e:
        logger.exception(f"[UPLOAD] 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail="파일 저장 중 오류 발생")
