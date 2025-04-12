# ----------------------
# file   : app/core/background_worker.py
# function: 업로드된 파일을 백그라운드 워커에서 처리 (중복 검사 → /data로 이동)
# ----------------------

import os
import shutil
from app.utils.hash_util import compute_sha256
import threading
import queue
from datetime import datetime
from pymongo import MongoClient
from loguru import logger

# ----------------------
# MongoDB 연결 설정 (동기)
# ----------------------
client = MongoClient("mongodb://host.docker.internal:27017")
db = client["noah_db"]
file_meta = db["file_meta"]
upload_queue = db["upload_queue"]

# ----------------------
# 워커 큐 및 스레드 수
# ----------------------
upload_task_queue = queue.Queue()
NUM_WORKERS = 4

# ----------------------
# param   : upload_id, file_name, temp_path
# function: 해시 검사 후 중복 체크 → /data 로 이동
# ----------------------
def process_upload(upload_id: str, file_name: str, temp_path: str):
    try:
        logger.info(f"[WORKER] {upload_id} / {file_name} 처리 시작")

        upload_queue.update_one(
            {"upload_id": upload_id, "file_name": file_name},
            {"$set": {"status": "processing"}}
        )

        # 해시 계산
        file_hash = compute_sha256(temp_path)

        # 중복 검사
        duplicate = file_meta.find_one({"file_hash": file_hash})
        if duplicate:
            upload_queue.update_one(
                {"upload_id": upload_id, "file_name": file_name},
                {"$set": {"status": "duplicate"}}
            )
            os.remove(temp_path)
            logger.info(f"[WORKER] {upload_id} / {file_name} 중복파일로 삭제됨")
            return

        # 썸네일 경로 가져오기 (없으면 "")
        upload_info = upload_queue.find_one({"upload_id": upload_id, "file_name": file_name})
        thumb_path = upload_info.get("thumb_path", "") if upload_info else ""

        # 최종 저장 위치: /data/파일명
        final_dir = "/data"
        os.makedirs(final_dir, exist_ok=True)

        final_path = os.path.join(final_dir, file_name)
        shutil.move(temp_path, final_path)

        # 메타데이터 저장
        file_meta.insert_one({
            "file_name": file_name,
            "file_path": final_path,
            "file_size": os.path.getsize(final_path),
            "file_hash": file_hash,
            "thumb_path": thumb_path,
            "tags": [],
            "status": "completed",
            "created_at": datetime.utcnow(),
        })

        upload_queue.update_one(
            {"upload_id": upload_id, "file_name": file_name},
            {"$set": {"status": "completed"}}
        )
        logger.info(f"[WORKER] {upload_id} / {file_name} 완료")

    except Exception:
        upload_queue.update_one(
            {"upload_id": upload_id, "file_name": file_name},
            {"$set": {"status": "failed"}}
        )
        logger.exception(f"[WORKER] {upload_id} / {file_name} 처리 실패")

# ----------------------
# function: 워커 루프 실행 (threading 사용)
# ----------------------
def worker_loop():
    while True:
        upload_id, file_name, temp_path = upload_task_queue.get()
        process_upload(upload_id, file_name, temp_path)
        upload_task_queue.task_done()

# ----------------------
# param   : upload_id, file_name, temp_path
# function: 워커에 작업 등록
# ----------------------
def enqueue(upload_id: str, file_name: str, temp_path: str):
    upload_task_queue.put((upload_id, file_name, temp_path))

# ----------------------
# function: 모든 워커 스레드 시작
# ----------------------
def start_workers():
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker_loop, daemon=True)
        t.start()
