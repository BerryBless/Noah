# 베이스 이미지: Python 3.10 사용
FROM python:3.10-slim

# ping 및 기타 유틸 설치
RUN apt-get update && apt-get install -y iputils-ping

# 작업 디렉토리 설정
WORKDIR /app

# requirements 복사 및 설치
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install debugpy

# 전체 프로젝트 복사
COPY . .

# FastAPI 실행 (uvicorn)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
