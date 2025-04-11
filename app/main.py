# app/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import upload, test_mongo, files
from app.core.limit_upload import LimitUploadSizeMiddleware
import os
from fastapi.staticfiles import StaticFiles
import logging
logger = logging.getLogger("uvicorn.error")
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
app.add_middleware(LimitUploadSizeMiddleware)

# ----------------------
# function: API 라우터 등록
# ----------------------
app.include_router(files.router, prefix="/api/files")
app.include_router(upload.router, prefix="/api/upload")
# app.include_router(test_mongo.router, prefix="/dev")  # ← 테스트용 API 경로

# ----------------------
# function: React 빌드된 UI를 FastAPI 경로에 mount (/ui)
# __file__ = /code/app/main.py
# → /code/front/dist로 접근하도록 경로 생성
# ----------------------
react_build_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "front", "dist"))
logger.info(f"React Build Path: {react_build_path}")
app.mount("/ui", StaticFiles(directory=react_build_path, html=True), name="frontend")