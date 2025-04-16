# ----------------------
# file   : app/utils/crawler.py
# function: RJ코드로 DLSite에서 제목, 썸네일, 태그 정보 크롤링
# return  : {title, thumbnail, tags}
# ----------------------

import requests
from bs4 import BeautifulSoup
from app.utils.logger import logger

def crawl_dlsite_info(rj_code: str):
    try:
        url = f"https://www.dlsite.com/maniax/work/=/product_id/{rj_code}.html"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"[CRAWLER] 접속 실패 - {url}")
            return None

        soup = BeautifulSoup(response.content, "lxml")

        # ----------------------
        # 제목 크롤링 - 정확한 구조 반영 (h1#work_name)
        # ----------------------
        title_element = soup.select_one("h1#work_name")
        title = title_element.text.strip() if title_element else "제목 없음"


        # ----------------------
        # 썸네일 이미지 크롤링 - srcset 또는 data-src 또는 src 순서로 탐색
        # ----------------------
        thumb_element = soup.select_one("div#work_left img")
        thumbnail = ""

        if thumb_element:
            thumbnail = (
                thumb_element.get("srcset") or
                thumb_element.get("data-src") or
                thumb_element.get("src") or
                ""
            )

        # 절대 URL 보정
        if thumbnail.startswith("//"):
            thumbnail = "https:" + thumbnail
        elif thumbnail.startswith("/"):
            thumbnail = "https://www.dlsite.com" + thumbnail


        # ----------------------
        # 태그 크롤링
        # ----------------------
        tag_elements = soup.select("div.main_genre a")
        tags = [tag.text.strip() for tag in tag_elements]

        return {
            "title": title,
            "thumbnail": thumbnail,
            "tags": tags,
        }

    except Exception as e:
        logger.exception(f"[CRAWLER] 크롤링 실패: {str(e)}")
        return None
