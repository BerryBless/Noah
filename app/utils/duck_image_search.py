# ----------------------
# file   : app/utils/duck_image_search.py
# function: DuckDuckGo 이미지 검색 (최대 N개 이미지 URL 반환)
# return  : [img_url, img_url, ...]
# ----------------------

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from app.utils.logger import logger
import re

def search_duckduckgo_images(keywords: str, max_results: int = 5) -> list[str]:
    try:
        logger.debug(f"[DUCK] DuckDuckGo 이미지 검색 시작: '{keywords}'")

        # ----------------------
        # 1차 요청: HTML 검색 → vqd 토큰 추출
        # ----------------------
        query = quote(keywords)
        search_url = f"https://duckduckgo.com/?q={query}&iax=images&ia=images"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:113.0) Gecko/20100101 Firefox/113.0",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://duckduckgo.com/"
        }

        res = requests.get(search_url, headers=headers, timeout=10)
        if res.status_code != 200:
            logger.warning(f"[DUCK] 1차 요청 실패: {search_url} → {res.status_code}")
            return []

        soup = BeautifulSoup(res.text, "lxml")

        # vqd 토큰 추출 (보강된 정규식)
        vqd_token = ""
        for script in soup.find_all("script"):
            if "vqd" in script.text:
                match = re.search(r"vqd[:=]['\"]?([a-zA-Z0-9_-]+)['\"]?", script.text)
                if match:
                    vqd_token = match.group(1)
                    break

        if not vqd_token:
            logger.warning("[DUCK] vqd 토큰 추출 실패")
            return []

        logger.debug(f"[DUCK] vqd 토큰 확보 완료: {vqd_token}")

        # ----------------------
        # 2차 요청: 이미지 JSON API 호출
        # ----------------------
        api_url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={query}&vqd={vqd_token}"
        res = requests.get(api_url, headers=headers, timeout=10)

        if res.status_code != 200:
            logger.warning(f"[DUCK] 이미지 API 요청 실패: {api_url} → {res.status_code}")
            return []

        json_data = res.json()
        raw_results = json_data.get("results", [])
        logger.debug(f"[DUCK] 이미지 API 응답 수: {len(raw_results)}개")

        # ----------------------
        # 3차 처리: 유효한 이미지 URL 필터링
        # ----------------------
        results = []
        for item in raw_results:
            image_url = item.get("image")
            if image_url and image_url.startswith("http"):
                base_url = image_url.split("?")[0].lower()
                if base_url.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    results.append(image_url)
                    if len(results) >= max_results:
                        break

        logger.debug(f"[DUCK] 최종 유효 이미지 URL 수: {len(results)}")
        for url in results:
            logger.debug(f"[DUCK] → {url}")

        return results

    except Exception as e:
        logger.exception(f"[DUCK] 이미지 검색 실패: {e}")
        return []
