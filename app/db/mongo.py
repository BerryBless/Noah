# ----------------------
# file   : app/db/mongo.py
# function: MongoDB 연결 객체 생성
# ----------------------

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# .env 로드
load_dotenv()

# ----------------------
# param   : MONGO_URI - 환경변수에서 가져옴 (기본값 포함)
# function: MongoDB 클라이언트 및 DB 객체 생성
# return  : db (AsyncIOMotorDatabase)
# ----------------------
MONGO_URI = os.getenv("MONGO_URI", "")

print(f"[DEBUG] MONGO_URI: {MONGO_URI}")
client = AsyncIOMotorClient(MONGO_URI)
db = client["noah_db"] 

# 기존 구조
file_meta = db["file_meta"]
tags = db["tags"]  # ← 이것을 "tags_collection"으로 쓰려면 아래처럼 alias 추가

# 명시적인 이름 추가
tags_collection = tags  