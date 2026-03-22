from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import shutil
import uuid
import os

from app.db.db import get_db
from app.db.models import User
from app.models.profile import UploadImageResponse, UserProfileResponse

router = APIRouter()

UPLOAD_DIR = "uploads"
ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"]

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/profile/upload", response_model=UploadImageResponse)
def upload_profile_image(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG and WEBP allowed")

    if user.profile_image and "default" not in user.profile_image:
        old_path = user.profile_image.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)

    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user.profile_image = f"/uploads/{filename}"
    db.commit()

    return UploadImageResponse(
        message="Profile image uploaded successfully",
        user_id=user.id,
        profile_image=user.profile_image
    )


@router.get("/profile/{user_id}", response_model=UserProfileResponse)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    image = user.profile_image if user.profile_image else "/uploads/default.png"

    return UserProfileResponse(
        user_id=user.id,
        username=user.username,
        name=user.name,
        email=user.email,
        profile_image=image
    )

