@echo off
set CONTAINER_NAME=noah-server

echo [0] 기존 컨테이너 중지 및 삭제
docker ps -a --filter "name=%CONTAINER_NAME%" --format "{{.ID}}" | findstr . > nul
if %errorlevel%==0 (
    echo [!] 기존 컨테이너 제거
    docker rm -f %CONTAINER_NAME%
)

echo [1] 프론트엔드 Vite 프로젝트 빌드
cd front
call npm install
call npm run build
cd ..

echo [2] Docker 이미지 캐시 없이 재빌드
docker compose build --no-cache

echo [3] 컨테이너 실행
docker compose up -d

echo [?] 실행 완료! 아래 주소를 확인하세요:
echo     - Swagger: http://localhost:8000/docs
echo     - 프론트 UI: http://localhost:8000/ui

pause
