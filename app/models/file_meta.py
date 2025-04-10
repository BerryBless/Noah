# ----------------------
# file   : app/models/file_meta.py
# function: 업로드된 파일의 메타 정보 스키마 정의
# ----------------------

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class FileMeta(BaseModel):
    file_name: str
    thumbnail_path: Optional[str] = ""
    tags: List[str] = []
    file_size: int
    file_hash: str
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
