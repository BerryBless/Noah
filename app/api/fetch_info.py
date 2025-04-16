# ----------------------
# file   : app/api/fetch_info.py
# function: RJ코드로 크롤링 API 제공
# ----------------------

from fastapi import APIRouter, Query
from app.utils.crawler import crawl_dlsite_info

router = APIRouter()

@router.get("/fetch-rj-info")
async def fetch_rj_info(rj_code: str = Query(..., description="RJ 코드 (예: RJ01169914)")):
    result = crawl_dlsite_info(rj_code)
    if result is None:
        return {"success": False, "message": "크롤링 실패"}
    return {"success": True, "data": result}
