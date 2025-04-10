# ----------------------
# file   : app/api/upload.py
# function: 모든 파일 업로드 처리 (확장자 제한 없음)
# ----------------------

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import os
import shutil
from app.services.worker import run_worker

router = APIRouter()

TEMP_DIR = "/data/temp"

# ----------------------
# 로거 설정
# ----------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ----------------------
# param   : file - 업로드된 파일
# function: 확장자 제한 없이 모든 파일 저장
# return  : 저장 완료 메시지
# ----------------------
@router.post("/file")
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_path = os.path.join(TEMP_DIR, file.filename)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"[UPLOAD] 임시 저장 완료: {temp_path}")
        
        background_tasks.add_task(run_worker, temp_path)
        
        return {"message": f"{file.filename} 임시 저장 완료, 중복 검사 중입니다."}

    except Exception as e:
        print(f"[ERROR] 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail="파일 저장 중 오류가 발생했습니다.")