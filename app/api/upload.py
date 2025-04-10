# ----------------------
# file   : app/api/upload.py
# function: 모든 파일 업로드 처리 (확장자 제한 없음)
# ----------------------

from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil

router = APIRouter()

UPLOAD_DIR = "/data"  # Docker 컨테이너에 마운트된 로컬 저장소

# ----------------------
# param   : file - 업로드된 파일
# function: 확장자 제한 없이 모든 파일 저장
# return  : 저장 완료 메시지
# ----------------------
@router.post("/file")
async def upload_file(file: UploadFile = File(...)):
    try:
        save_path = os.path.join(UPLOAD_DIR, file.filename)

        # 파일 저장
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"message": f"{file.filename} 저장 완료"}
    
    except Exception as e:
        # 예외 로그 출력 (추후 로거 연동)
        print(f"[ERROR] 파일 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="파일 저장 중 오류가 발생했습니다.")
