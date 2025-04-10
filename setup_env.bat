@echo off
echo [1] 가상환경 생성 중...
python -m venv venv

echo [2] 가상환경 활성화...
call venv\Scripts\activate

echo [3] pip 업그레이드...
python -m pip install --upgrade pip

echo [4] requirements.txt 설치 중...
pip install -r requirements.txt

echo [✔] 설치 완료!
pause
