from pydantic import BaseModel


class UploadImageResponse(BaseModel):
    message: str
    profile_image: str


class UserProfileResponse(BaseModel):
    username: str
    name: str
    email: str
    profile_image: str
    code: str


class UpdateUserRequest(BaseModel):
    username: str | None = None
    name: str | None = None
