import hashlib

# ----------------------
# param   : path - 파일 경로
# function: SHA256 해시 계산
# return  : 해시 문자열
# ----------------------
def compute_sha256(path: str) -> str:
    hash_sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()
