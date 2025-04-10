# ----------------------
# file   : app/api/test_mongo.py
# function: MongoDB 연결 테스트용 API
# ----------------------

from fastapi import APIRouter
from app.db.mongo import db

router = APIRouter()

# ----------------------
# function: 파일 메타 더미 데이터 삽입
# return  : 삽입된 문서 ID
# ----------------------
@router.get("/mongo/test-insert")
async def test_insert():
    result = await db.file_meta.insert_one({
        "name": "test_file.zip",
        "tags": ["AI", "test", "fastapi"],
    })
    return {"inserted_id": str(result.inserted_id)}

# ----------------------
# function: 파일 이름으로 문서 검색
# return  : 첫 번째 매칭 문서
# ----------------------
@router.get("/mongo/test-find")
async def test_find():
    doc = await db.file_meta.find_one({"name": "test_file.zip"})
    if doc:
        doc["_id"] = str(doc["_id"])  # ObjectId는 JSON 직렬화 위해 문자열로 변환
    return doc
