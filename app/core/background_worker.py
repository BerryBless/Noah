
# ----------------------
# file   : app/core/background_worker.py
# function: 업로드된 파일을 백그라운드 워커에서 처리 (중복 검사 → /data로 이동)
# ----------------------

import os
import shutil
import hashlib
import threading
import queue
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
import asyncio

# ----------------------
# MongoDB 연결 설정
# ----------------------
client = AsyncIOMotorClient("mongodb://host.docker.internal:27017")
db = client["noah_db"]
file_meta = db["file_meta"]
upload_queue = db["upload_queue"]

# ----------------------
# 워커 큐 및 스레드 수
# ----------------------
upload_task_queue = queue.Queue()
NUM_WORKERS = 4

# ----------------------
# param   : file_path
# function: SHA-256 해시 계산
# return  : 문자열 해시값
# ----------------------
def calc_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

# ----------------------
# param   : upload_id, temp_path
# function: 해시 검사 후 중복 체크 → /data 로 이동
# ----------------------
async def process_upload(upload_id: str, temp_path: str):
    try:
        logger.info(f"[WORKER] {upload_id} 처리 시작")
        await upload_queue.update_one({"upload_id": upload_id}, {"$set": {"status": "processing"}})

        # 해시 계산
        file_hash = calc_hash(temp_path)

        # 중복 검사
        duplicate = await file_meta.find_one({"file_hash": file_hash})
        if duplicate:
            await upload_queue.update_one({"upload_id": upload_id}, {"$set": {"status": "duplicate"}})
            os.remove(temp_path)
            logger.info(f"[WORKER] {upload_id} 중복파일로 삭제됨")
            return

        # DB에서 원본 파일명 추출
        upload_info = await upload_queue.find_one({"upload_id": upload_id})
        original_filename = upload_info["file_name"]

        # 최종 저장 위치: /data/파일명
        final_dir = "/data"
        os.makedirs(final_dir, exist_ok=True)  # ✅ /data 디렉토리 없으면 생성

        final_path = os.path.join(final_dir, original_filename)
        shutil.move(temp_path, final_path)

        # DB 등록
        await file_meta.insert_one({
            "file_name": original_filename,
            "file_path": final_path,
            "file_size": os.path.getsize(final_path),
            "file_hash": file_hash,
            "thumb_path": upload_info.get("thumb_path", ""),
            "tags": [],
            "status": "completed",
            "created_at": datetime.utcnow(),
        })

        # 업로드 완료 상태 반영
        await upload_queue.update_one({"upload_id": upload_id}, {"$set": {"status": "completed"}})
        logger.info(f"[WORKER] {upload_id} 완료")

    except Exception as e:
        await upload_queue.update_one({"upload_id": upload_id}, {"$set": {"status": "failed"}})
        logger.exception(f"[WORKER] {upload_id} 처리 실패")

# ----------------------
# function: 워커 루프 실행 (스레드 내부에서 이벤트 루프 생성)
# ----------------------
def worker_loop():
    def thread_main():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def loop_worker():
            while True:
                upload_id, temp_path = await loop.run_in_executor(None, upload_task_queue.get)
                try:
                    await process_upload(upload_id, temp_path)
                except Exception:
                    logger.exception(f"[WORKER] {upload_id} 처리 실패 (루프 내부)")
                finally:
                    upload_task_queue.task_done()

        loop.run_until_complete(loop_worker())

    threading.Thread(target=thread_main, daemon=True).start()

# ----------------------
# param   : upload_id, temp_path
# function: 큐에 작업 등록
# ----------------------
def enqueue(upload_id: str, temp_path: str):
    upload_task_queue.put((upload_id, temp_path))

# ----------------------
# function: 여러 워커 스레드 시작
# ----------------------
def start_workers():
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker_loop, daemon=True)
        t.start()
