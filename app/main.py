# app/main.py

from fastapi import FastAPI
from app.api import upload, test_mongo

app = FastAPI()

app.include_router(upload.router, prefix="/upload")
app.include_router(test_mongo.router, prefix="/dev")  # ← 테스트용 API 경로
