@echo off
set CONTAINER_NAME=noah-server

echo [0] 기존 컨테이너 확인 및 종료...
docker ps -a --filter "name=%CONTAINER_NAME%" --format "{{.ID}}" | findstr . > nul
if %errorlevel%==0 (
    echo [!] 기존 컨테이너 중지 및 삭제
    docker rm -f %CONTAINER_NAME%
)

echo [1] docker compose로 noah-server 컨테이너 빌드 및 실행
docker compose up --build -d

echo  실행 완료! 브라우저에서 http://localhost:8000/docs 확인 가능
pause
