# app/main.py

from app.core import background_worker
from app.utils.logger import logger
import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.staticfiles import StaticFiles
from app.api import upload, get_upload_id, ws_upload, files, proxy_download
from app.api import fetch_info
from app.api import maintenance
#from app.core.limit_upload import LimitUploadSizeMiddleware

app = FastAPI()

# ----------------------
# function: 썸네일 이미지 접근 경로 설정 (/thumbs → /data/thumbs)
# ----------------------
if not os.path.exists("/data/thumbs"):
    os.makedirs("/data/thumbs")
app.mount("/thumbs", StaticFiles(directory="/data/thumbs"), name="thumbs")

# ----------------------
# function: 최대 100GB 제한 미들웨어 추가
# ----------------------
#app.add_middleware(LimitUploadSizeMiddleware)

# ----------------------
# function: API 라우터 등록
# ----------------------
app.include_router(upload.router)
app.include_router(get_upload_id.router) 
app.include_router(ws_upload.router)
app.include_router(files.router, prefix="/api/files")
app.include_router(proxy_download.router)  
app.include_router(fetch_info.router, prefix="/api")
app.include_router(maintenance.router, prefix="/api/maintenance")

# ----------------------
# function: React 빌드된 UI를 FastAPI 경로에 mount (/ui)
# __file__ = /code/app/main.py
# → /code/front/dist로 접근하도록 경로 생성
# ----------------------

ui_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "front", "dist"))
app.mount("/ui", StaticFiles(directory=ui_path, html=True), name="frontend")

logger.info(f"React Build Path: {ui_path}")

@ app.middleware("http")
async def spa_redirect(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/ui") and response.status_code == 404:
        index_path = os.path.join(ui_path, "index.html")
        return FileResponse(index_path)
    return response




# ----------------------
# 백그라운드 워커 시작 (서버 시작 시)
# ----------------------
@app.on_event("startup")
async def startup_event():
    logger.info("[INIT] WorkerPool 초기화 시작")
    background_worker.start_workers()
    logger.info("[INIT] WorkerPool 초기화 완료")