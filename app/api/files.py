# ----------------------
# file   : app/api/files.py
# function: 업로드된 파일 메타 목록 조회
# ----------------------

from fastapi import APIRouter, HTTPException, Query, Form
from fastapi.responses import FileResponse
from app.db.mongo import db
from app.models.file_meta import FileMeta
from typing import List, Optional
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
@router.get("/", response_model=None)
async def get_files(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100)):
    try:
        skip = (page - 1) * size

        total = await db.file_meta.count_documents({})
        cursor = db.file_meta.find().sort("created_at", -1).skip(skip).limit(size)
        raw_items = await cursor.to_list(length=size)

        # ----------------------
        # 모든 태그 ObjectId 수집
        # ----------------------
        tag_id_set = set()
        for item in raw_items:
            raw_tags = item.get("tags", [])
            if isinstance(raw_tags, list):
                tag_id_set.update(raw_tags)
            else:
                tag_id_set.add(raw_tags)

        # ----------------------
        # 태그 이름 매핑 가져오기
        # ----------------------
        tag_map = {}
        if tag_id_set:
            tag_cursor = db.tags.find({"_id": {"$in": list(tag_id_set)}})
            async for tag in tag_cursor:
                tag_map[tag["_id"]] = tag["tag_name"]

        # ----------------------
        # 변환된 결과 구성 - 태그명, 썸네일 포함
        # ----------------------
        items = []
        for item in raw_items:
            item.pop("_id", None)
            item["file_hash"] = item.get("file_hash")

            raw_tags = item.get("tags", [])
            if isinstance(raw_tags, list):
                item["tags"] = [tag_map.get(tid, str(tid)) for tid in raw_tags]
            else:
                item["tags"] = [tag_map.get(raw_tags, str(raw_tags))]

            item["thumbnail_path"] = os.path.basename(item.get("thumbnail_path", "")) # 썸네일 명시 포함
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
# param   : file_hash - 다운로드할 파일의 해시 문자열
# function: 파일 경로에서 직접 파일 반환
# return  : FileResponse (application/octet-stream)
# ----------------------
@router.get("/download/{file_hash}")
async def download_file_by_hash(file_hash: str):
    try:
        # 파일 메타데이터 조회
        meta = await db.file_meta.find_one({"file_hash": file_hash})
        if not meta:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        file_path = os.path.join(DATA_DIR, meta["file_name"])
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="파일이 서버에 존재하지 않습니다.")

        # 실제 파일 응답
        return FileResponse(
            path=file_path,
            filename=meta["file_name"],
            media_type="application/octet-stream"  
        )

    except Exception as e:
        logger.exception(f"[DOWNLOAD] 파일 다운로드 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="파일 다운로드 중 오류가 발생했습니다.")



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


# ----------------------
# param   : file_hash - 대상 파일의 고유 해시
# param   : tags - 새로 설정할 태그 문자열 리스트
# function: 기존 태그 제거 및 새 태그 반영 (tag_count 갱신 포함)
# return  : 수정 결과 메시지
# ----------------------
@router.put("/file/tag")
async def update_file_tags(
    file_hash: str = Form(...),
    tags: List[str] = Form(default=[])
):
    try:
        # ----------------------
        # 파일 조회
        # ----------------------
        meta = await db.file_meta.find_one({"file_hash": file_hash})
        if not meta:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        old_tag_ids = meta.get("tags", [])

        # ----------------------
        # 기존 태그 count 감소
        # ----------------------
        from app.services.tag_manager import (
            decrease_tag_count_on_delete,
            process_tags_on_upload
        )
        await decrease_tag_count_on_delete(db, old_tag_ids)

        # ----------------------
        # 새 태그 처리 (중복이면 count 증가)
        # ----------------------
        new_tag_ids = await process_tags_on_upload(db, tags, is_new_file=True)

        # ----------------------
        # DB 업데이트
        # ----------------------
        await db.file_meta.update_one(
            {"file_hash": file_hash},
            {"$set": {"tags": new_tag_ids}}
        )

        return {"message": f"{meta['file_name']} 태그가 수정되었습니다.", "tags": tags}

    except Exception as e:
        logger.exception(f"[TAG-UPDATE] 태그 수정 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="태그 수정 중 오류가 발생했습니다.")


# ----------------------
# param   : q - 검색어 (선택, 없으면 전체 반환)
# function: 태그명 검색 (부분일치, 대소문자 무시)
# return  : 태그 리스트 [{tag_name, tag_count}]
# ----------------------
@router.get("/tags")
async def search_tags(q: Optional[str] = None, limit: int = 20):
    try:
        query = {}
        if q:
            query = {"tag_name": {"$regex": q, "$options": "i"}}  # i = 대소문자 무시

        cursor = db.tags.find(query).sort("tag_count", -1).limit(limit)
        tags = await cursor.to_list(length=limit)

        for tag in tags:
            tag.pop("_id", None)

        return tags

    except Exception as e:
        logger.exception(f"[TAGS] 태그 검색 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="태그 검색 중 오류가 발생했습니다.")


# ----------------------
# param   : tag - 태그명 (선택)
# param   : keyword - 파일명 검색 키워드 (선택)
# param   : page - 페이지 번호 (1부터)
# function: 태그 + 키워드 기반 파일 검색, 10개 단위 페이징
# return  : {"total", "page", "items": [...]}
# ----------------------
@router.get("/files/search")
async def search_files(
    tag: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1)
):
    try:
        # ----------------------
        # 조건 구성 (태그/키워드)
        # ----------------------
        query = {}
        if tag:
            tag_doc = await db.tags.find_one({"tag_name": tag})
            if not tag_doc:
                raise HTTPException(status_code=404, detail="해당 태그를 찾을 수 없습니다.")
            query["tags"] = tag_doc["_id"]

        if keyword:
            query["file_name"] = {"$regex": keyword, "$options": "i"}

        size = 10
        skip = (page - 1) * size

        total = await db.file_meta.count_documents(query)
        cursor = db.file_meta.find(query).sort("created_at", -1).skip(skip).limit(size)
        raw_items = await cursor.to_list(length=size)

        # ----------------------
        # 결과 구성 (태그 문자열 + 썸네일 포함)
        # ----------------------
        items = []
        for item in raw_items:
            item.pop("_id", None)
            item["file_hash"] = item.get("file_hash")
            
            item["tags"] = [str(t) for t in item.get("tags", [])]
            item["thumbnail_path"] =  os.path.basename(item.get("thumbnail_path", "")) # 썸네일 명시 포함
            items.append(item)

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[SEARCH] 복합 검색 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="파일 검색 중 오류가 발생했습니다.")