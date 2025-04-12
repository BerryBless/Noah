import os
import aiohttp
import uuid
import shutil
import re
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from app.db.mongo import file_meta
from app.utils.hash_util import compute_sha256
from app.utils.logger import logger

router = APIRouter()

# ----------------------
# route   : POST /proxy-download
# param   : {
#   "url": 다운로드할 원본 URL,
#   "cookie": (옵션) 쿠키 문자열,
#   "referer": (옵션) 리퍼러
# }
# function: 확장 프로그램이 감지한 다운로드 URL을 서버에서 직접 다운로드
# return  : { status, file_name }
# ----------------------
@router.post("/proxy-download")
async def proxy_download(request: Request):
    try:
        # ----------------------
        # 클라이언트로부터 요청 JSON 파싱
        # ----------------------
        data = await request.json()
        url = data.get("url")
        cookie_str = data.get("cookie", "")
        referer = data.get("referer")

        if not url:
            raise HTTPException(status_code=400, detail="URL is required")

        # ----------------------
        # 기본 헤더 설정 (User-Agent + Referer)
        # ----------------------
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        if referer:
            headers["Referer"] = referer

        # ----------------------
        # 쿠키 문자열을 dict로 변환
        # ----------------------
        cookies = {}
        for part in cookie_str.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                cookies[k] = v

        # ----------------------
        # 서버에서 파일 다운로드 수행
        # ----------------------
        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            try:
                async with session.get(url, ssl=False, allow_redirects=True) as resp:
                    if resp.content_type.startswith("text/html") or resp.content_length == 0:
                        logger.error(f"[PROXY_DOWNLOAD] 콘텐츠 타입 오류 - content_type: {resp.content_type}")
                        raise HTTPException(status_code=500, detail="Invalid content type")
                    if resp.status != 200:
                        logger.error(f"[PROXY_DOWNLOAD] 응답 실패 - status: {resp.status}")
                        raise HTTPException(status_code=500, detail="Download failed")

                    # ----------------------
                    # Content-Disposition에서 파일 이름 추출
                    # ----------------------
                    disposition = resp.headers.get("Content-Disposition")
                    if disposition and "filename=" in disposition:
                        filename_match = re.findall('filename="?([^\";]+)"?', disposition)
                        if filename_match:
                            filename = filename_match[0]
                        else:
                            filename = url.split("/")[-1].split("?")[0] or f"download_{uuid.uuid4()}"
                    else:
                        filename = url.split("/")[-1].split("?")[0] or f"download_{uuid.uuid4()}"

                    # ----------------------
                    # 파일 저장 (임시 경로)
                    # ----------------------
                    os.makedirs("/data/temp", exist_ok=True)
                    temp_path = f"/data/temp/{uuid.uuid4()}_{filename}"

                    with open(temp_path, "wb") as f:
                        while True:
                            chunk = await resp.content.read(1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
            except Exception as e:
                logger.exception("[PROXY_DOWNLOAD] aiohttp 요청 중 예외 발생")
                raise HTTPException(status_code=500, detail="Download failed")

        # ----------------------
        # SHA256 해시 계산 및 중복 검사
        # ----------------------
        file_hash = compute_sha256(temp_path)
        existing = await file_meta.find_one({"file_hash": file_hash})
        if existing:
            os.remove(temp_path)
            return {
                "status": "duplicate",
                "file_name": filename
            }

        # ----------------------
        # 최종 경로로 이동 및 DB 저장
        # ----------------------
        os.makedirs("/data", exist_ok=True)
        final_path = f"/data/{filename}"
        shutil.move(temp_path, final_path)

        await file_meta.insert_one({
            "file_name": filename,
            "file_path": final_path,
            "file_size": os.path.getsize(final_path),
            "file_hash": file_hash,
            "created_at": datetime.utcnow(),
            "status": "completed",
            "tags": [],
            "thumb_path": ""
        })

        return {
            "status": "success",
            "file_name": filename
        }

    except Exception as e:
        logger.exception("[PROXY_DOWNLOAD] 서버 다운로드 실패")
        raise HTTPException(status_code=500, detail=str(e))