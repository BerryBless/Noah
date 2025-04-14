# ----------------------
# file   : app/services/worker.py
# function: 업로드된 파일을 워커에서 중복 검사 및 이동 처리
# ----------------------

import os
import shutil
from app.utils.logger import logger
from datetime import datetime
from typing import List
from app.models.file_meta import FileMeta
from app.services.tag_manager import process_tags_on_upload
from app.db.mongo_sync import sync_db
from app.utils.hash_util import compute_sha256

DATA_DIR = "/data"
TEMP_DIR = "/data/temp"


# ----------------------
# param   : temp_path - 임시 저장된 파일 경로
# param   : tags - 업로드 시 전달된 태그 문자열 리스트
# param   : thumb_path - 클라이언트에서 업로드한 썸네일 이미지 경로 (선택)
# function: 해시 중복 검사 후 data로 이동 및 메타/태그 처리
# return  : None
# ----------------------
async def run_worker(temp_path: str, tags: List[str], thumb_path: str = ""):
    try:
        file_name = os.path.basename(temp_path)
        file_size = os.path.getsize(temp_path)
        file_hash = await compute_sha256(temp_path)

        logger.info(f"[WORKER] 파일 처리 시작: {file_name}, 해시: {file_hash}")

        # 중복 검사
        existing = await db.file_meta.find_one({"file_hash": file_hash})
        is_new_file = existing is None

        if not is_new_file:
            os.remove(temp_path)
            if thumb_path:
                thumb_abs = os.path.join("/data", "thumbs", os.path.basename(thumb_path))
                if os.path.exists(thumb_abs):
                    os.remove(thumb_abs)
            logger.info(f"[WORKER] 중복 파일 삭제됨: {file_name}")
            return

        # 태그 처리
        tag_ids = await process_tags_on_upload(db, tags, is_new_file)

        # data로 이동
        final_path = os.path.join(DATA_DIR, file_name)
        shutil.move(temp_path, final_path)
        logger.info(f"[WORKER] 파일 이동 완료: {file_name} → {final_path}")

        # 메타데이터 저장
        meta = FileMeta(
            file_name=file_name,
            file_size=file_size,
            file_hash=file_hash,
            thumb_path=thumb_path,
            tags=tag_ids,
            created_at=datetime.utcnow(),
        )

        await db.file_meta.insert_one(meta.dict())
        logger.info(f"[WORKER] 메타데이터 등록 완료: {file_name} + 태그 {tags}")

    except Exception as e:
        logger.exception(f"[WORKER] 처리 중 예외 발생: {e}")


# ----------------------
# function: 스레드 기반 워커 함수 (MongoDB 동기 접근용)
# ----------------------
def run_worker_sync(temp_path: str, tags: List[str], thumb_path: str = ""):
    try:
        global sync_db
        from app.services.tag_manager import process_tags_on_upload_sync  # 동기 버전 따로 작성

        file_name = os.path.basename(temp_path)
        file_size = os.path.getsize(temp_path)
        file_hash = compute_sha256(temp_path)

        logger.info(f"[WORKER] 파일 처리 시작: {file_name}, 해시: {file_hash}")

        existing = sync_db.file_meta.find_one({"file_hash": file_hash})
        is_new_file = existing is None

        if not is_new_file:
            os.remove(temp_path)
            logger.info(f"[WORKER] 중복 파일 삭제됨: {file_name}")
            return

        tag_ids = process_tags_on_upload_sync(sync_db, tags, is_new_file)

        final_path = os.path.join(DATA_DIR, file_name)
        shutil.move(temp_path, final_path)
        logger.info(f"[WORKER] 파일 이동 완료: {final_path}")

        meta = {
            "file_name": file_name,
            "file_size": file_size,
            "file_hash": file_hash,
            "thumb_path": thumb_path,
            "tags": tag_ids,
            "created_at": datetime.utcnow(),
        }

        sync_db.file_meta.insert_one(meta)
        logger.info(f"[WORKER] 메타데이터 등록 완료: {file_name}")

    except Exception as e:
        logger.exception(f"[WORKER] 예외 발생: {e}")
        
