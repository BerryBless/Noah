# ----------------------
# file   : app/api/get_upload_id.py
# function: 고유 업로드 ID 발급 API
# return  : {"upload_id": "UUID"}
# ----------------------
from fastapi import APIRouter
import uuid

router = APIRouter()

@router.get("/get-upload-id")
async def get_upload_id():
    upload_id = str(uuid.uuid4())
    return {"upload_id": upload_id}
