# ----------------------
# file   : app/utils/keyword_extractor.py
# function: BERT 기반 키워드 추출기 (멀티랭귀지 지원)
# ----------------------

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from app.utils.logger import logger

# 모델은 최초 1회만 로드
kw_model = KeyBERT(SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2"))

def extract_keywords(text: str, top_n: int = 5):
    try:
        if not text:
            return []

        # 키워드 추출
        keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words=None,
            top_n=top_n
        )

        # 결과만 리스트로 반환
        return [kw[0] for kw in keywords]

    except Exception as e:
        logger.exception(f"[KEYBERT] 키워드 추출 실패: {e}")
        return []
