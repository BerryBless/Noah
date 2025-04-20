# ----------------------
# file   : app/api/maintenance.py
# function: 기존 파일들을 해시_파일명 형식으로 일괄 리네임
# ----------------------

from fastapi import APIRouter, HTTPException
import os
from app.utils.logger import logger
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import APIRouter
from app.db.mongo import db
from app.utils.crawler import crawl_dlsite_info
from app.utils.logger import logger
import re
import requests
from io import BytesIO


MONGO_URI = os.getenv("MONGO_URI", "")
router = APIRouter()

client = AsyncIOMotorClient(MONGO_URI)
db = client["noah_db"]
file_meta = db["file_meta"]

# ----------------------
# function: 기존 파일들 중 file_path를 해시_파일명 형식으로 통일
# return  : { "updated": int }
# ----------------------
@router.post("/admin/fix-filenames")
async def fix_filenames_to_hash_prefix():
    updated_count = 0

    cursor = file_meta.find({})
    async for doc in cursor:
        file_name = doc.get("file_name")
        file_hash = doc.get("file_hash")
        file_path = doc.get("file_path")

        if not file_name or not file_hash or not file_path:
            continue

        # 이미 해시가 붙은 형식이면 skip
        if os.path.basename(file_path).startswith(file_hash):
            continue

        # 새 경로 구성
        new_filename = f"{file_hash}_{file_name}"
        new_path = os.path.join("/data", new_filename)

        try:
            os.rename(file_path, new_path)
            await file_meta.update_one(
                {"_id": doc["_id"]},
                {"$set": {"file_path": new_path}}
            )
            logger.info(f"[RENAME] {file_path} → {new_path}")
            updated_count += 1

        except Exception as e:
            logger.error(f"[RENAME-FAIL] {file_path} → {new_path}: {str(e)}")

    return {"updated": updated_count}



@router.post("/admin/fetch-rj-batch")
async def fetch_rj_batch():
    try:
        query = {
            "tags": {"$in": [[], None]},
            "file_name": {"$regex": "RJ\\d{4,}", "$options": "i"}
        }
        cursor = db.file_meta.find(query)
        updated = 0
        skipped = 0

        async for file in cursor:
            file_name = file.get("file_name", "")
            file_hash = file.get("file_hash")
            rj_match = re.search(r"RJ\d{4,}", file_name, re.IGNORECASE)
            if not rj_match:
                skipped += 1
                continue

            rj_code = rj_match.group(0).upper()
            result = crawl_dlsite_info(rj_code)
            if not result:
                logger.warning(f"[SKIP] 크롤링 실패: {file_name}")
                skipped += 1
                continue

            # 썸네일 다운로드
            thumb_path = ""
            try:
                response = requests.get(result["thumbnail"])
                ext = result["thumbnail"].split(".")[-1]
                filename = f"{file_hash}.{ext}"
                thumb_path = f"thumbs/{filename}"
                with open(f"/data/{thumb_path}", "wb") as f:
                    f.write(response.content)
            except Exception as e:
                logger.warning(f"[SKIP] 썸네일 저장 실패: {file_name}, {e}")

            update_fields = {
                "tags": result["tags"],
            }
            if thumb_path:
                update_fields["thumb_path"] = filename

            await db.file_meta.update_one(
                {"file_hash": file_hash},
                {"$set": update_fields}
            )
            logger.info(f"[UPDATE] {rj_code} → {file_name}")
            updated += 1

        return {"updated": updated, "skipped": skipped}

    except Exception as e:
        logger.exception("[BATCH] RJ 자동 태그 크롤링 실패")
        return {"error": str(e)}