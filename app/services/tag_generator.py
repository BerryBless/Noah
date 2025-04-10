# ----------------------
# file   : app/services/tag_generator.py
# function: 파일명 기반 AI 태그 생성
# ----------------------

from keybert import KeyBERT
import aiohttp
from bs4 import BeautifulSoup
import re

kw_model = KeyBERT()

# ----------------------
# param   : file_name - zip 파일명
# function: 웹 검색 후 본문에서 키워드 추출
# return  : 태그 리스트
# ----------------------
async def generate_tags(file_name: str) -> list[str]:
    query = re.sub(r"\.zip$", "", file_name, flags=re.IGNORECASE)
    text = await search_web_text(query)
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words="english", top_n=10)
    return [kw[0] for kw in keywords]

# ----------------------
# param   : query - 검색어
# function: DuckDuckGo 검색 후 본문 텍스트 추출
# return  : 텍스트
# ----------------------
async def search_web_text(query: str) -> str:
    url = f"https://html.duckduckgo.com/html/?q={query}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text()
