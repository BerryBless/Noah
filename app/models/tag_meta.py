# ----------------------
# file   : app/models/tag_meta.py
# function: 태그 정보와 해당 태그를 사용하는 파일 수 저장
# ----------------------

from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId

class TagMeta(BaseModel):
    id: Optional[ObjectId] = Field(alias="_id")
    tag_name: str
    tag_count: int = 0

    # ----------------------
    # Pydantic v2에서 사용자 정의 타입(ObjectId) 허용
    # ----------------------
    model_config = {
        "arbitrary_types_allowed": True
    }