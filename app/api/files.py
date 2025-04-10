# ----------------------
# file   : app/api/files.py
# function: 업로드된 파일 메타 목록 조회
# ----------------------

from fastapi import APIRouter, HTTPException, Query, Body, Path
from app.db.mongo import db
from app.models.file_meta import FileMeta
from typing import List, Optional
import os
from fastapi import Path

DATA_DIR = "/data"

router = APIRouter()


# ----------------------
# param   : page - 현재 페이지 번호 (기본 1)
# param   : size - 페이지 당 항목 수 (기본 10)
# param   : tags - AND 조건으로 포함해야 할 태그 목록 (옵션)
# function: 태그 필터링 및 페이징을 통해 파일 메타데이터 조회
# return  : {"total": 전체 개수, "page": 현재 페이지, "size": 페이지 크기, "items": 파일 리스트}
# ----------------------
@router.get("/", response_model=dict)
async def get_files(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    tags: Optional[List[str]] = Query(None, description="AND 조건 태그 필터")
):
    try:
        skip = (page - 1) * size

        # 태그가 지정되었을 경우 AND 조건 필터 적용, 없으면 전체 조회
        query = {"tags": {"$all": tags}} if tags else {}

        # 총 개수 계산
        total = await db.file_meta.count_documents(query)

        # 목록 조회 (created_at 기준 최신 정렬)
        cursor = db.file_meta.find(query).sort("created_at", -1).skip(skip).limit(size)
        items = await cursor.to_list(length=size)

        # ObjectId 제거
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
