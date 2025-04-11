# app/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import upload, test_mongo, files
from app.core.limit_upload import LimitUploadSizeMiddleware
import os
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
app.include_router(files.router, prefix="/files")
app.include_router(upload.router, prefix="/upload")
# app.include_router(test_mongo.router, prefix="/dev")  # ← 테스트용 API 경로