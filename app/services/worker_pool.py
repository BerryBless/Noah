# ----------------------
# file   : app/services/worker_pool.py
# function: 파일 업로드 처리를 위한 워커 스레드 풀 + 작업 큐 정의
# ----------------------

import threading
import queue
from app.utils.logger import logger
from typing import List, Optional

from app.services.worker import run_worker_sync

# ----------------------
# 전역 태스크 큐 (스레드 안전)
# ----------------------
task_queue = queue.Queue()

# ----------------------
# class   : Worker
# function: 대기 중인 작업을 꺼내서 run_worker_sync 호출
# ----------------------
class Worker(threading.Thread):
    def run(self):
        while True:
            try:
                temp_path, tags, thumbnail_path = task_queue.get()
                run_worker_sync(temp_path, tags, thumbnail_path)
                task_queue.task_done()
            except Exception as e:
                logger.exception("[WORKER] 처리 중 예외 발생: %s", e)

# ----------------------
# class   : WorkerPool
# function: 워커 스레드를 미리 생성해둔 스레드 풀
# ----------------------
class WorkerPool:
    def __init__(self, num_workers=4):
        for _ in range(num_workers):
            worker = Worker()
            worker.daemon = True  # 앱 종료 시 자동 종료
            worker.start()

    # ----------------------
    # param   : temp_path - 임시 저장 경로
    # param   : tags - 태그 문자열 리스트
    # param   : thumbnail_path - 썸네일 경로
    # function: 작업 큐에 업로드 작업 추가
    # ----------------------
    def add_task(self, temp_path: str, tags: List[str], thumbnail_path: Optional[str] = ""):
        task_queue.put((temp_path, tags, thumbnail_path))

# ----------------------
# 글로벌 워커풀 참조 관리
# ----------------------
_worker_pool: Optional[WorkerPool] = None

def set_worker_pool(pool: WorkerPool):
    global _worker_pool
    _worker_pool = pool

def get_worker_pool() -> Optional[WorkerPool]:
    return _worker_pool