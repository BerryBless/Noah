# app/main.py

from fastapi import FastAPI
from app.api import upload, files
from app.core.limit_upload import LimitUploadSizeMiddleware

import os
if os.getenv("DEBUG_MODE", "0") == "1":
    import debugpy
    print("[DEBUG] Waiting for debugger attach on port 5678...")
    debugpy.listen(("0.0.0.0", 5678))
    debugpy.wait_for_client()

    
app = FastAPI()

# 최대 100GB 제한 미들웨어 추가
app.add_middleware(LimitUploadSizeMiddleware)

app.include_router(files.router, prefix="/files")
app.include_router(upload.router, prefix="/upload")
#app.include_router(test_mongo.router, prefix="/dev")  # ← 테스트용 API 경로
