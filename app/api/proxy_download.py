import os
import aiohttp
import uuid
import shutil
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from app.db.mongo import file_meta  # MongoDB 컬렉션 직접 import
from app.utils.hash_util import compute_sha256
from app.utils.logger import logger

router = APIRouter()


# ----------------------
# route   : POST /proxy-download
# param   : { "url": "<다운로드 URL>" }
# function: 서버가 URL을 직접 다운로드하여 Noah 서버에 저장
# return  : { status, file_name }
# ----------------------
@router.post("/proxy-download")
async def proxy_download(request: Request):
    try:
        data = await request.json()
        url = data.get("url")

        if not url:
            raise HTTPException(status_code=400, detail="URL is required")

        # ----------------------
        # 파일 다운로드 (서버에서 직접)
        # ----------------------
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, ssl=False) as resp:
                    if resp.status != 200:
                        logger.error(f"[PROXY_DOWNLOAD] 응답 실패 - status: {resp.status}")
                        raise HTTPException(status_code=500, detail="Download failed")

                    filename = url.split("/")[-1]
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
        # 해시 계산
        # ----------------------
        file_hash = compute_sha256(temp_path)

        # ----------------------
        # 중복 검사 (해시 기반)
        # ----------------------
        existing = await file_meta.find_one({"file_hash": file_hash})
        if existing:
            os.remove(temp_path)
            return {
                "status": "duplicate",
                "file_name": filename
            }

        # ----------------------
        # 파일 최종 경로로 이동
        # ----------------------
        os.makedirs("/data", exist_ok=True)
        final_path = f"/data/{filename}"
        shutil.move(temp_path, final_path)

        # ----------------------
        # 메타데이터 저장
        # ----------------------
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
