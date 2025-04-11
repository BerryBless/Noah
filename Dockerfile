# 1단계: React 앱 빌드
FROM node:18 AS frontend-build
WORKDIR /app
COPY front/ ./front/
WORKDIR /app/front
RUN npm install && npm run build

# 2단계: Python 서버 이미지
FROM python:3.10
WORKDIR /code

# FastAPI + 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY app/ ./app/
COPY --from=frontend-build /app/front/dist ./front/dist

# 서버 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
