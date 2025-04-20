# ----------------------
# file   : app/utils/clip_image_selector.py
# function: 텍스트 키워드와 가장 유사한 이미지 URL 선택 (CLIP 사용)
# return  : best_image_url 또는 None
# ----------------------

import requests
from PIL import Image
from io import BytesIO
from transformers import CLIPProcessor, CLIPModel
import torch
from app.utils.logger import logger

# ----------------------
# 전역 모델 & 프로세서 (최초 1회 로드)
# ----------------------
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

def select_best_image_by_clip(image_urls: list[str], text_prompt: str) -> str | None:
    try:
        images = []
        valid_urls = []

        # ----------------------
        # 유효한 이미지 로딩
        # ----------------------
        for url in image_urls:
            try:
                res = requests.get(url, timeout=5)
                image = Image.open(BytesIO(res.content)).convert("RGB")
                images.append(image)
                valid_urls.append(url)
            except Exception as e:
                logger.warning(f"[CLIP] 이미지 로딩 실패: {url} / {e}")
                continue

        if not images:
            return None

        # ----------------------
        # CLIP 유사도 계산
        # ----------------------
        inputs = clip_processor(text=[text_prompt] * len(images), images=images, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = clip_model(**inputs)

        scores = outputs.logits_per_image.softmax(dim=0).squeeze().tolist()

        # ----------------------
        # 가장 높은 점수의 이미지 선택
        # ----------------------
        best_idx = scores.index(max(scores))
        return valid_urls[best_idx]

    except Exception as e:
        logger.exception(f"[CLIP] 유사 이미지 선택 실패: {e}")
        return None
