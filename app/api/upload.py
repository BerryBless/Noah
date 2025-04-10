# app/api/upload.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def test_upload():
    return {"message": "upload router OK"}
