# ----------------------
# file   : app/routes/file.py
# function: 파일 업로드 API - 모든 파일 허용 + 태그 직접 전달
# ----------------------

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Form, HTTPException
from typing import List, Optional
import os
import shutil
import logging
from app.services.worker import run_worker
from app.services.tag_manager import split_tags

router = APIRouter()
logger = logging.getLogger(__name__)

TEMP_DIR = "/data/temp"

# ----------------------
# param   : file - 업로드된 파일
# param   : tags - 태그 문자열 리스트 (FormData로 전달)
# function: 파일을 임시 저장하고, 태그 리스트를 워커로 전달
# return  : 저장 완료 메시지
# ----------------------
@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    tags: Optional[List[str]] = Form(default=[]),
    background_tasks: BackgroundTasks = None
):
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_path = os.path.join(TEMP_DIR, file.filename)

    try:
        # ----------------------
        # 파일 저장
        # ----------------------
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"[UPLOAD] 임시 저장 완료: {temp_path}")

        # ----------------------
        # 백그라운드 태스크로 워커 실행 (태그 포함)
        # ----------------------\
        cleaned_tags = split_tags(tags)
        background_tasks.add_task(run_worker, temp_path, cleaned_tags)

        return {"message": f"{file.filename} 임시 저장 완료, 중복 검사 중입니다."}

    except Exception as e:
        logger.exception(f"[UPLOAD] 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail="파일 저장 중 오류가 발생했습니다.")
