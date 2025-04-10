# ----------------------
# file   : app/services/worker.py
# function: 업로드된 파일을 워커에서 중복 검사 및 이동 처리
# ----------------------

import os
import hashlib
import shutil
import logging
from app.db.mongo import db
from app.models.file_meta import FileMeta
from datetime import datetime

DATA_DIR = "/data"
TEMP_DIR = "/data/temp"

# ----------------------
# 로거 설정
# ----------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ----------------------
# param   : temp_path - 임시 저장된 파일 경로
# function: 해시 중복 검사 후 data로 이동 또는 삭제
# return  : None
# ----------------------
async def run_worker(temp_path: str):
    try:
        file_name = os.path.basename(temp_path)
        file_size = os.path.getsize(temp_path)
        file_hash = await get_file_hash(temp_path)

        logger.info(f"[WORKER] 파일 처리 시작: {file_name}, 해시: {file_hash}")

        # 중복 검사
        existing = await db.file_meta.find_one({"file_hash": file_hash})
        if existing:
            os.remove(temp_path)
            logger.info(f"[WORKER] 중복 파일 발견 → 삭제됨: {file_name}")
            return

        # data로 이동
        final_path = os.path.join(DATA_DIR, file_name)
        shutil.move(temp_path, final_path)
        logger.info(f"[WORKER] 파일 이동 완료: {file_name} → {final_path}")

        meta = FileMeta(
            file_name=file_name,
            file_size=file_size,
            file_hash=file_hash,
            thumbnail_path="",  # 썸네일 생성 예정
            tags=[],  # 태그 생성 예정
            created_at=datetime.utcnow(),
        )

        await db.file_meta.insert_one(meta.dict())
        logger.info(f"[WORKER] 메타데이터 등록 완료: {file_name}")

    except Exception as e:
        logger.error(f"[WORKER] 처리 중 예외 발생: {e}")

# ----------------------
# function: 파일 해시(SHA256) 계산
# return  : 해시 문자열
# ----------------------
async def get_file_hash(path: str) -> str:
    hash_sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()
