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
from datetime import datetime

DATA_DIR = "/data"

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



# ----------------------
# function: 전체 크롤링
# ----------------------
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

# ----------------------
# function: 모든 파일의 무결성 검사 (DB 기록과 실제 파일 비교)
# return  : {total, checked, broken: [{file_hash, file_name, reason}]}
# ----------------------
from datetime import datetime
DATA_DIR = "/data"
THUMB_DIR = os.path.join(DATA_DIR, "thumbs")

@router.post("/verify-and-clean")
async def verify_and_cleanup_files():
    total = 0
    removed = 0
    error_logged = 0

    try:
        cursor = db.file_meta.find()
        async for file in cursor:
            total += 1
            file_name = file.get("file_name")
            file_hash = file.get("file_hash")
            expected_size = file.get("file_size")
            thumb_path = file.get("thumb_path", "")

            file_path = file.get("file_path")
            reason = ""

            # 원본 파일 확인
            if not os.path.exists(file_path):
                reason = "file not found"
            elif os.path.getsize(file_path) != expected_size:
                reason = f"size mismatch (expected {expected_size}, actual {os.path.getsize(file_path)})"

            # 썸네일 확인
            # if not reason:  # 파일은 정상일 때만 검사
            #     if not thumb_path:
            #         reason = "thumbnail path missing"
            #     else:
            #         thumb_full_path = os.path.join(DATA_DIR, thumb_path.lstrip("/"))
            #         if not os.path.exists(thumb_full_path):
            #             reason = f"thumbnail not found at {thumb_path}"

            if reason:
                file["reason"] = reason
                file["moved_at"] = datetime.utcnow()
                await db.error_log.insert_one(file)
                await db.file_meta.delete_one({"file_hash": file_hash})

                removed += 1
                error_logged += 1
                logger.warning(f"[INTEGRITY] 손상 항목 이동됨: {file_name} - {reason}")

        return {
            "total": total,
            "removed": removed,
            "error_logged": error_logged
        }

    except Exception as e:
        logger.exception(f"[INTEGRITY] 무결성 검사 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="무결성 검사 실패")


# ----------------------
# file   : app/api/files.py
# route  : /api/files/recover-all
# function: error_log → file_meta 복구 (파일/썸네일 검사 포함, 실패 시 recover_failed_log에 기록)
# return  : 결과 요약
# ----------------------


@router.post("/admin/recover-all")
async def recover_all_files():
    total = 0
    recovered = 0
    skipped = 0
    failed = 0

    try:
        cursor = db.error_log.find()
        async for entry in cursor:
            total += 1
            file_hash = entry.get("file_hash")
            file_name = entry.get("file_name")
            expected_size = entry.get("file_size")
            thumb_path = entry.get("thumb_path", "")

            # file_meta에 이미 존재하는 경우 스킵
            existing = await db.file_meta.find_one({"file_hash": file_hash})
            if existing:
                skipped += 1
                continue

            # 원본 파일 확인
            file_path = os.path.join(DATA_DIR, file_name)
            if not os.path.exists(file_path) or os.path.getsize(file_path) != expected_size:
                await db.recover_failed_log.insert_one({
                    "file_hash": file_hash,
                    "reason": "original file invalid",
                    "attempted_at": datetime.utcnow()
                })
                failed += 1
                continue

            # 썸네일 확인 (있을 경우만)
            if thumb_path:
                thumb_full_path = os.path.join(DATA_DIR, thumb_path.lstrip("/"))
                if not os.path.exists(thumb_full_path):
                    await db.recover_failed_log.insert_one({
                        "file_hash": file_hash,
                        "reason": "thumbnail not found",
                        "attempted_at": datetime.utcnow()
                    })
                    failed += 1
                    continue

            # 복구 처리
            entry.pop("_id", None)
            entry.pop("reason", None)
            entry.pop("moved_at", None)

            await db.file_meta.insert_one(entry)
            await db.error_log.delete_one({"file_hash": file_hash})
            recovered += 1
            logger.info(f"[RECOVER] 복구 완료: {file_hash}")

        return {
            "total_attempted": total,
            "successfully_recovered": recovered,
            "skipped_due_to_existing": skipped,
            "failed_to_recover": failed
        }

    except Exception as e:
        logger.exception(f"[RECOVER-ALL] 일괄 복구 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="일괄 복구 중 오류 발생")
