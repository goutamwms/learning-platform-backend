import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.schemas import UploadResponse

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads/topics")
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1] or ".bin"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    return UploadResponse(url=f"/uploads/topics/{filename}")
