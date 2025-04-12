# ----------------------
# file   : app/services/tag_manager.py
# function: 태그 생성, 참조 수 증감 등 태그 관련 DB 처리
# ----------------------

from typing import List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.utils.logger import logger
from app.models.tag_meta import TagMeta


# ----------------------
# param   : db - MongoDB 세션
# param   : tag_names - 유저가 보낸 태그 문자열 리스트
# param   : is_new_file - 중복 검사 결과 새 파일 여부
# function: 태그 ObjectId 리스트 반환 + 필요 시 tag_count 증가
# return  : List[ObjectId]
# ----------------------
async def process_tags_on_upload(db: AsyncIOMotorDatabase, tag_names: List[str], is_new_file: bool) -> List[ObjectId]:
    tag_ids = []
    for tag in tag_names:
        try:
            tag_doc = await db.tags.find_one({"tag_name": tag})
            if tag_doc:
                if is_new_file:
                    await db.tags.update_one(
                        {"_id": tag_doc["_id"]},
                        {"$inc": {"tag_count": 1}}
                    )
                tag_ids.append(tag_doc["_id"])
            else:
                tag_count = 1 if is_new_file else 0
                result = await db.tags.insert_one({
                    "tag_name": tag,
                    "tag_count": tag_count
                })
                tag_ids.append(result.inserted_id)
        except Exception as e:
            logger.exception(f"태그 처리 중 오류 발생: {tag} - {e}")
    return tag_ids

# ----------------------
# param   : db - MongoDB 세션
# param   : tag_ids - 삭제될 파일이 가지고 있던 태그 id 리스트
# function: 파일 삭제 시 해당 태그들의 tag_count 감소
# return  : None
# ----------------------
async def decrease_tag_count_on_delete(db: AsyncIOMotorDatabase, tag_ids: List[ObjectId]):
    for tag_id in tag_ids:
        try:
            await db.tags.update_one(
                {"_id": tag_id},
                {"$inc": {"tag_count": -1}}
            )
        except Exception as e:
            logger.exception(f"태그 카운트 감소 중 오류 발생: {tag_id} - {e}")

            
# ----------------------
# function: 쉼표로 구분된 태그 분리 및 공백 제거
# ----------------------
def split_tags(raw_tags: List[str]) -> List[str]:
    result = []
    for tag in raw_tags:
        parts = tag.split(",")  # 쉼표로 분리
        result.extend(part.strip() for part in parts if part.strip())
    return result

# ----------------------
# param   : db - pymongo DB 인스턴스
# param   : tag_names - 유저가 보낸 태그 문자열 리스트
# param   : is_new_file - 중복 검사 결과 새 파일 여부
# function: 동기 pymongo 버전 태그 처리
# return  : 태그 ObjectId 리스트
# ----------------------
def process_tags_on_upload_sync(db, tag_names: List[str], is_new_file: bool) -> List[ObjectId]:
    tag_ids = []
    for tag in tag_names:
        try:
            tag_doc = db.tags.find_one({"tag_name": tag})
            if tag_doc:
                if is_new_file:
                    db.tags.update_one(
                        {"_id": tag_doc["_id"]},
                        {"$inc": {"tag_count": 1}}
                    )
                tag_ids.append(tag_doc["_id"])
            else:
                tag_count = 1 if is_new_file else 0
                result = db.tags.insert_one({
                    "tag_name": tag,
                    "tag_count": tag_count
                })
                tag_ids.append(result.inserted_id)
        except Exception as e:
            logger.exception(f"[SYNC] 태그 처리 중 오류 발생: {tag} - {e}")
    return tag_ids
