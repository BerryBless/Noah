# ----------------------
# file   : app/db/mongo_sync.py
# function: pymongo 기반 동기 MongoDB 클라이언트
# ----------------------

from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)

sync_db = client["noah_db"]
