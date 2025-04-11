@echo off
set CONTAINER_NAME=noah-server

echo [0] ���� �����̳� ���� �� ����
docker ps -a --filter "name=%CONTAINER_NAME%" --format "{{.ID}}" | findstr . > nul
if %errorlevel%==0 (
    echo [!] ���� �����̳� ����
    docker rm -f %CONTAINER_NAME%
)

echo [1] ����Ʈ���� Vite ������Ʈ ����
cd front
call npm install
call npm run build
cd ..

echo [2] Docker �̹��� ĳ�� ���� �����
docker compose build --no-cache

echo [3] �����̳� ����
docker compose up -d

echo [?] ���� �Ϸ�! �Ʒ� �ּҸ� Ȯ���ϼ���:
echo     - Swagger: http://localhost:8000/docs
echo     - ����Ʈ UI: http://localhost:8000/ui

pause
