# ----------------------
# file   : app/api/files.py
# function: 업로드된 파일 메타 목록 조회
# ----------------------

from fastapi import APIRouter, HTTPException, Query
from app.db.mongo import db
from app.models.file_meta import FileMeta
from typing import List
import os
from fastapi import Path
from bson import ObjectId
from fastapi import HTTPException
import logging

DATA_DIR = "/data"

router = APIRouter()
logger = logging.getLogger(__name__)

# ----------------------
# param   : page - 현재 페이지 번호 (1부터)
# param   : size - 페이지당 항목 수
# function: 페이징된 파일 메타 목록 반환
# return  : {"total": 전체 수, "items": [FileMeta...]}
# ----------------------
@router.get("/", response_model=None)  # ← dict 대신 None 또는 따로 모델 정의 추천
async def get_files(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100)):
    try:
        skip = (page - 1) * size

        total = await db.file_meta.count_documents({})
        cursor = db.file_meta.find().sort("created_at", -1).skip(skip).limit(size)
        raw_items = await cursor.to_list(length=size)

        items = []
        for item in raw_items:
            item.pop("_id", None)

            # 'tags'가 None이거나 ObjectId 한 개일 경우도 리스트로 보장
            raw_tags = item.get("tags", [])
            if isinstance(raw_tags, list):
                item["tags"] = [str(t) for t in raw_tags]
            else:
                item["tags"] = [str(raw_tags)]

            items.append(item)

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items
        }

    except Exception as e:
        print(f"[ERROR] 파일 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="파일 목록 조회 중 오류 발생")





# ----------------------
# param   : file_hash - 삭제할 파일의 해시 문자열
# function: 파일 삭제 및 tag_count 감소 처리
# return  : 삭제 완료 메시지
# ----------------------
@router.delete("/file/hash/{file_hash}")
async def delete_file_by_hash(file_hash: str):
    try:
        # ----------------------
        # 파일 메타데이터 조회
        # ----------------------
        meta = await db.file_meta.find_one({"file_hash": file_hash})
        if not meta:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        file_path = os.path.join(DATA_DIR, meta["file_name"])
        tag_ids = meta.get("tags", [])

        # ----------------------
        # 파일 삭제
        # ----------------------
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"[DELETE] 실제 파일 삭제됨: {file_path}")
        else:
            logger.warning(f"[DELETE] 파일 경로 없음 (DB만 존재): {file_path}")

        # ----------------------
        # 메타데이터 삭제
        # ----------------------
        await db.file_meta.delete_one({"file_hash": file_hash})
        logger.info(f"[DELETE] 메타데이터 삭제 완료: {file_hash}")

        # ----------------------
        # 태그 카운트 감소
        # ----------------------
        from app.services.tag_manager import decrease_tag_count_on_delete
        await decrease_tag_count_on_delete(db, tag_ids)

        return {"message": f"{meta['file_name']} 삭제 완료, 관련 태그 카운트 감소됨."}

    except Exception as e:
        logger.exception(f"[DELETE] 파일 삭제 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="파일 삭제 중 오류가 발생했습니다.")
