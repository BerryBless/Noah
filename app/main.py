# app/main.py

from fastapi import FastAPI
from app.api import upload, test_mongo, files
from app.core.limit_upload import LimitUploadSizeMiddleware

app = FastAPI()

# 최대 100GB 제한 미들웨어 추가
app.add_middleware(LimitUploadSizeMiddleware)

app.include_router(files.router, prefix="/files")
app.include_router(upload.router, prefix="/upload")
#app.include_router(test_mongo.router, prefix="/dev")  # ← 테스트용 API 경로
