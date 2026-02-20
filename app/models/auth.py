from pydantic import BaseModel

class UserDetails(BaseModel):
    email: str
    username: str
    name: str