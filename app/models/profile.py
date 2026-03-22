from pydantic import BaseModel


class UploadImageResponse(BaseModel):
    message: str
    user_id: int
    profile_image: str


class UserProfileResponse(BaseModel):
    user_id: int
    username: str
    name: str
    email: str
    profile_image: str