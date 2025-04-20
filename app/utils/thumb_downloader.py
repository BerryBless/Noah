# ----------------------
# file   : app/utils/thumb_downloader.py
# function: 이미지 URL을 다운로드 후 썸네일로 저장
# return  : 저장된 썸네일 경로 or None
# ----------------------

import os
import requests
from PIL import Image
from io import BytesIO
from app.utils.logger import logger

THUMB_DIR = "/data/thumbs"

def download_and_save_thumbnail(image_url: str, file_hash: str) -> str | None:
    try:
        if not os.path.exists(THUMB_DIR):
            os.makedirs(THUMB_DIR, exist_ok=True)

        response = requests.get(image_url, timeout=10)
        image = Image.open(BytesIO(response.content)).convert("RGB")

        # 저장 경로 지정
        save_path = os.path.join(THUMB_DIR, f"{file_hash}.jpg")
        image.save(save_path, format="JPEG")

        logger.info(f"[THUMB] 썸네일 저장 완료: {save_path}")
        return f"/thumbs/{file_hash}.jpg"

    except Exception as e:
        logger.exception(f"[THUMB] 썸네일 저장 실패: {e}")
        return None


# ----------------------
# function: 썸네일 경로를 file_meta에 반영
# ----------------------

from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = os.getenv("MONGO_URI", "")
client = AsyncIOMotorClient(MONGO_URI)
db = client["noah_db"]

async def update_thumb_path(file_hash: str, thumb_path: str):
    try:
        await db.file_meta.update_one(
            {"file_hash": file_hash},
            {"$set": {"thumb_path": thumb_path}}
        )
        logger.info(f"[THUMB] DB 업데이트 완료: {file_hash} → {thumb_path}")
    except Exception as e:
        logger.exception(f"[THUMB] DB 업데이트 실패: {e}")
