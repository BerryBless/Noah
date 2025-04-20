# ----------------------
# file   : app/api/maintenance.py
# function: 기존 파일들을 해시_파일명 형식으로 일괄 리네임
# ----------------------

from fastapi import APIRouter, HTTPException
import os
from app.utils.logger import logger
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter()

client = AsyncIOMotorClient("mongodb://host.docker.internal:27017")
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
