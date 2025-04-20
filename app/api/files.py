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
from app.utils.logger import logger
import shutil
from app.services.tag_manager import get_tag_names_by_ids

from motor.motor_asyncio import AsyncIOMotorClient
import re
# db테스트
from bson.json_util import dumps
from fastapi.responses import JSONResponse

DATA_DIR = "/data"
MONGO_URI = os.getenv("MONGO_URI", "")

router = APIRouter()
client = AsyncIOMotorClient(MONGO_URI)
db = client["noah_db"]

# ----------------------
# param   : page - 현재 페이지 번호 (1부터)
# param   : size - 페이지당 항목 수
# function: 완료된 업로드만 페이징하여 파일 메타 목록 반환
# return  : {"total": 전체 수, "page": 현재 페이지, "size": 페이지당 수, "items": [파일 정보]}
# ----------------------
@router.get("/", response_model=None)
async def get_files(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100),sort: str = Query("created")):
    try:

        # ----------------------
        # 완료된 파일만 필터링
        # ----------------------
        skip = (page - 1) * size
        query = {"status": "completed"}
                # 정렬 기준 설정
        sort_field = "created_at" if sort == "created" else "file_name"
        sort_order = -1 if sort == "created" else 1

        total = await db.file_meta.count_documents(query)
        cursor = db.file_meta.find(query, collation={"locale": "ko", "strength": 1}).sort(sort_field, sort_order).skip(skip).limit(size)
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
        logger.info(f"[SEARCH DEBUG] query={query}")

        items = []
        for item in raw_items:
            item.pop("_id", None)
            item["file_hash"] = item.get("file_hash")

            raw_tags = item.get("tags", [])
            if isinstance(raw_tags, list):
                item["tags"] = [tag_map.get(tid, str(tid)) for tid in raw_tags]
            else:
                item["tags"] = [tag_map.get(raw_tags, str(raw_tags))]

            # 썸네일 파일명만 추출
            thumb_path = item.get("thumb_path", "") or item.get("thumb_path", "")
            item["thumb_path"] = os.path.basename(thumb_path)
            item["file_name"] = item.get("file_name", "")

            items.append(item)

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items
        }

    except Exception as e:
        logger.exception("[FILES] 파일 목록 조회 실패")
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

        file_path = os.path.join(DATA_DIR, meta["file_path"])
        original_name = meta["file_name"]

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="파일이 서버에 존재하지 않습니다.")

        # 실제 파일 응답
        return FileResponse(
            path=file_path,
            filename=original_name,
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

        # 썸네일 삭제
        thumb_path = meta.get("thumb_path", "")
        if thumb_path:
            abs_thumb_path = os.path.join("/data", "thumbs", os.path.basename(thumb_path))
            if os.path.exists(abs_thumb_path):
                os.remove(abs_thumb_path)
                logger.info(f"[DELETE] 썸네일 삭제 완료: {abs_thumb_path}")


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
# param   : sort - 정렬 기준 ("created" 또는 "name")
# function: 태그 또는 키워드 기반 파일 검색 + 페이징 + 정렬 + 한글 collation 대응
# return  : {"total", "page", "size", "items": [...]}
# ----------------------
@router.get("/search")
async def search_files(
    tag: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    sort: str = Query("created")
):
    logger.info(f"[SEARCH DEBUG] tag={tag}, keyword={keyword}, page={page}, sort={sort}")
    
    try:
        # ----------------------
        # 검색 조건 구성
        # ----------------------
        query = {"status": "completed"}

        if tag:
            tag_doc = await db.tags.find_one({"tag_name": tag})
            if not tag_doc:
                raise HTTPException(status_code=404, detail="해당 태그를 찾을 수 없습니다.")
            query["tags"] = tag_doc["_id"]

        elif keyword:
            query["file_name"] = {"$regex": keyword, "$options": "i"}

        else:
            raise HTTPException(status_code=400, detail="tag 또는 keyword 중 하나는 반드시 입력되어야 합니다.")

        logger.info(f"[SEARCH DEBUG] tag={tag}, keyword={keyword}, query={query}")

        # ----------------------
        # 정렬 및 페이징 설정
        # ----------------------
        size = 10
        skip = (page - 1) * size
        sort_field = "created_at" if sort == "created" else "file_name"
        sort_order = -1 if sort == "created" else 1

        # ----------------------
        # MongoDB 쿼리 실행 (한글 대응 collation 포함)
        # ----------------------
        total = await db.file_meta.count_documents(query)
        cursor = db.file_meta.find(query, collation={"locale": "ko", "strength": 1}) \
            .sort(sort_field, sort_order) \
            .skip(skip) \
            .limit(size)

        raw_items = await cursor.to_list(length=size)

        # ----------------------
        # 결과 구성
        # ----------------------
        items = []
        for item in raw_items:
            item.pop("_id", None)
            item["file_hash"] = item.get("file_hash", "")


            #태그 이름
            tag_ids = item.get("tags", [])
            tag_names = await get_tag_names_by_ids(db, tag_ids)
            item["tags"] = tag_names
            
            item["thumb_path"] = os.path.basename(item.get("thumb_path", ""))
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


# ----------------------
# function: file_hash 기준으로 파일 정보 조회 (수정용)
# ----------------------
@router.get("/file/hash/{file_hash}")
async def get_file_meta(file_hash: str):
    doc = await db.file_meta.find_one({"file_hash": file_hash})
    if not doc:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    from app.services.tag_manager import get_tag_names_by_ids
    tag_names = await get_tag_names_by_ids(db, doc.get("tags", []))

    return {
        "file_name": doc.get("file_name", ""),
        "tags": tag_names,
        "thumb_path": os.path.basename(doc.get("thumb_path", ""))
    }

# ----------------------
# file   : app/api/files.py
# function: file_hash 기준으로 파일명, 썸네일, 태그 한 번에 수정
# ----------------------

from fastapi import UploadFile, File, Form
from typing import List

@router.put("/meta")
async def update_file_metadata(
    file_hash: str = Form(...),
    file_name: str = Form(...),
    tags: List[str] = Form(default=[]),
    thumb: UploadFile = File(None)
):
    try:
        # ----------------------
        # 기존 메타 조회
        # ----------------------
        meta = await db.file_meta.find_one({"file_hash": file_hash})
        if not meta:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        update_fields = {"file_name": file_name}

        # ----------------------
        # 썸네일 교체 처리
        # ----------------------
        if thumb:
            old_thumb = meta.get("thumb_path", "")
            if old_thumb:
                abs_path = os.path.join("/data/thumbs", os.path.basename(old_thumb))
                if os.path.exists(abs_path):
                    os.remove(abs_path)

            thumbs_dir = os.path.join("/data", "thumbs")
            os.makedirs(thumbs_dir, exist_ok=True)
                # 썸네일 이름에 file_hash prefix 추가
            new_thumb_name = f"{file_hash}_{thumb.filename}"
            new_thumb_path = os.path.join(thumbs_dir, new_thumb_name)

            with open(new_thumb_path, "wb") as f:
                shutil.copyfileobj(thumb.file, f)

            update_fields["thumb_path"] = f"/thumbs/{new_thumb_name}"

        # ----------------------
        # 태그 전처리 (공백 제거 및 빈 값 제거)
        # ----------------------
        cleaned_tags = [tag.strip() for tag in tags if tag.strip()]
        logger.debug(f"[META-UPDATE] 수신된 tags: {tags} → 정제 후: {cleaned_tags}")

        # ----------------------
        # 태그 처리 (기존 감소 + 새 증가)
        # ----------------------
        from app.services.tag_manager import (
            decrease_tag_count_on_delete,
            process_tags_on_upload
        )

        old_tags = meta.get("tags", [])
        await decrease_tag_count_on_delete(db, old_tags)

        new_tag_ids = await process_tags_on_upload(db, cleaned_tags, is_new_file=True)
        update_fields["tags"] = new_tag_ids


        # ----------------------
        # 실제 파일명 변경 처리 (file_name 변경 시)
        # ----------------------
        old_file_path = os.path.join(DATA_DIR, meta["file_name"])
        new_file_path = os.path.join(DATA_DIR, file_name)

        if old_file_path != new_file_path:
            if os.path.exists(old_file_path):
                os.rename(old_file_path, new_file_path)
                logger.info(f"[META-UPDATE] 파일명 변경됨: {old_file_path} → {new_file_path}")

                # 실제 경로가 바뀌었으므로 DB의 file_path도 함께 수정
                update_fields["file_path"] = new_file_path
            else:
                logger.warning(f"[META-UPDATE] 실제 파일이 존재하지 않음: {old_file_path}")

        # ----------------------
        # DB 업데이트
        # ----------------------
        await db.file_meta.update_one(
            {"file_hash": file_hash},
            {"$set": update_fields}
        )

        return {"message": "파일 정보가 성공적으로 수정되었습니다."}

    except Exception as e:
        logger.exception(f"[META-UPDATE] 파일 메타데이터 수정 중 예외 발생: {e}")
        raise HTTPException(status_code=500, detail="파일 메타데이터 수정 중 오류 발생")
    



# ----------------------
# function: 파일명에서 단어 추출
# ----------------------
def normalize(text: str) -> str:
    # 대소문자 무시, 특수문자 제거, 전부 붙이기
    return re.sub(r"[^\w가-힣]", "", text.lower())

def tokenize(text: str) -> set:
    # 1. 먼저 띄어쓰기 기준 분할
    base = re.sub(r"[^\w가-힣]", " ", text.lower())
    words = base.split()

    # 2. 추가로 붙어있는 형태를 나눠서 탐지 (슬라이딩 윈도우식)
    merged = normalize(text)
    chunks = re.findall(r"[가-힣]+|[a-z]+|[0-9]+", merged)

    tokens = set(words + chunks)

    # 조사 제거
    stopwords = {"입니다", "하다", "의", "에", "이", "가", "을", "를", "다", "zip", "ver"}
    filtered = {t for t in tokens if t not in stopwords and len(t) > 1}

    return set(sorted(filtered))

# ----------------------
# function: 자카드 유사도 계산
# ----------------------
def jaccard_similarity(set1, set2):
    if not set1 or not set2:
        return 0
    return len(set1 & set2) / len(set1 | set2)


# ----------------------
# API: 유사 파일 그룹핑
# ----------------------
@router.get("/grouped")
async def get_grouped_files():
    all_files = await db.file_meta.find({}).to_list(length=None)
    tokenized = [(f, tokenize(f["file_name"])) for f in all_files]

    # 로그: 파일명 + 토큰 확인
    # for f, tokens in tokenized:
    #     logger.debug(f"[GROUPING] {f['file_name']} → {tokens}")

    used = set()
    groups = []

    for i, (file_i, tokens_i) in enumerate(tokenized):
        if i in used:
            continue

        group = [dict(file_i)]
        used.add(i)

        for j in range(i + 1, len(tokenized)):
            if j in used:
                continue

            file_j, tokens_j = tokenized[j]
            sim = jaccard_similarity(tokens_i, tokens_j)

            #logger.debug(f"[COMPARE] {file_i['file_name']} ↔ {file_j['file_name']} = {sim:.2f}")

            if sim >= 0.4:
                group.append(dict(file_j))
                used.add(j)

        if len(group) > 1:
            cleaned_group = []
            for item in group:
                item = dict(item)
                item.pop("_id", None)

                # ObjectId → str 변환 (tags 필드 등)
                if "tags" in item and isinstance(item["tags"], list):
                    item["tags"] = [str(t) for t in item["tags"]]
                elif isinstance(item.get("tags"), ObjectId):
                    item["tags"] = [str(item["tags"])]

                item["thumb_path"] = os.path.basename(item.get("thumb_path", "") or "")
                item["file_name"] = item.get("file_name", "")
                item["file_hash"] = item.get("file_hash", "")
                item["file_size"] = item.get("file_size", 0)

                cleaned_group.append(item)
            groups.append(cleaned_group)

    return {"groups": groups}

@router.get("/all")
async def get_all_files(sort: str = Query("created", enum=["created", "name"])):
    sort_field = "created_at" if sort == "created" else "file_name"
    direction = -1 if sort == "created" else 1

    cursor = db.file_meta.find({}).sort(sort_field, direction)
    raw_items = await cursor.to_list(length=None)

    return JSONResponse(
        content=dumps({
            "items": raw_items,
            "total": len(raw_items)
        }),
        media_type="application/json"
    )