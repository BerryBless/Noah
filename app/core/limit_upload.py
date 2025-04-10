# ----------------------
# file   : app/core/limit_upload.py
# function: 요청 바디 크기 제한 미들웨어 (기본: 100GB)
# ----------------------

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException

MAX_BODY_SIZE = 100 * 1024 * 1024 * 1024  # 100GB

class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            raise HTTPException(status_code=413, detail="파일이 너무 큽니다 (최대 100GB 허용).")
        return await call_next(request)
