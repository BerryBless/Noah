from fastapi import FastAPI
from app.api import upload

app = FastAPI(title="NAS AI Tag Server")

app.include_router(upload.router, prefix="/upload")