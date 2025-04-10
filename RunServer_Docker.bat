@echo off
set CONTAINER_NAME=noah-server

echo [0] ���� �����̳� Ȯ�� �� ����...
docker ps -a --filter "name=%CONTAINER_NAME%" --format "{{.ID}}" | findstr . > nul
if %errorlevel%==0 (
    echo [!] ���� �����̳� ���� �� ����
    docker rm -f %CONTAINER_NAME%
)

echo [1] docker compose�� noah-server �����̳� ���� �� ����
docker compose up --build -d

echo  ���� �Ϸ�! ���������� http://localhost:8000/docs Ȯ�� ����
pause
