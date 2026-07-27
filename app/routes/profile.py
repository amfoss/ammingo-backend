from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import shutil
import uuid
import os

from app.db.db import get_db
from app.db.models import User
from app.models.profile import (
    UploadImageResponse,
    UserProfileResponse,
    UpdateUserRequest,
)
from app.middlewares.verify_token import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads"
ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"]

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/profile/upload", response_model=UploadImageResponse)
def upload_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG and WEBP allowed")

    if current_user.profile_image and "default" not in current_user.profile_image:
        old_path = current_user.profile_image.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)

    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    current_user.profile_image = f"/uploads/{filename}"
    db.commit()

    return UploadImageResponse(
        message="Profile image uploaded successfully",
        user_id=current_user.id,
        profile_image=current_user.profile_image,
    )


@router.get("/profile/{user_id}", response_model=UserProfileResponse)
def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    image = user.profile_image if user.profile_image else "/uploads/default.png"

    return UserProfileResponse(
        username=user.username,
        name=user.name,
        email=user.email,
        profile_image=image,
        code=user.code,
    )


@router.patch("/profile/me", response_model=UserProfileResponse)
def update_user_profile(
    data: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if data.username is not None:
        existing = (
            db.query(User)
            .filter(User.username == data.username, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = data.username

    if data.name is not None:
        current_user.name = data.name

    db.commit()
    db.refresh(current_user)

    return UserProfileResponse(
        user_id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        email=current_user.email,
        profile_image=(
            current_user.profile_image
            if current_user.profile_image
            else "/uploads/default.png"
        ),
        code=current_user.code,
    )
