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

DATA_DIR = "/data"

router = APIRouter()

# ----------------------
# param   : page - 현재 페이지 번호 (1부터)
# param   : size - 페이지당 항목 수
# function: 페이징된 파일 메타 목록 반환
# return  : {"total": 전체 수, "items": [FileMeta...]}
# ----------------------
@router.get("/", response_model=dict)
async def get_files(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100)):
    try:
        skip = (page - 1) * size

        total = await db.file_meta.count_documents({})
        cursor = db.file_meta.find().sort("created_at", -1).skip(skip).limit(size)
        items = await cursor.to_list(length=size)

        # ID 제거
        for item in items:
           item.pop("_id", None)

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
# param   : file_hash - 삭제할 파일의 고유 해시값
# function: 해시로 파일 및 메타데이터 삭제
# return  : 삭제 결과 메시지
# ----------------------
@router.delete("/by-hash/{file_hash}")
async def delete_file_by_hash(file_hash: str):
    try:
        file_doc = await db.file_meta.find_one({"file_hash": file_hash})
        if not file_doc:
            raise HTTPException(status_code=404, detail="해당 해시의 파일 없음")

        file_name = file_doc["file_name"]
        file_path = os.path.join(DATA_DIR, file_name)

        if os.path.exists(file_path):
            os.remove(file_path)

        await db.file_meta.delete_one({"file_hash": file_hash})
        return {"message": f"{file_name} 삭제 완료"}

    except Exception as e:
        print(f"[ERROR] 해시 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="삭제 중 오류가 발생했습니다.")
