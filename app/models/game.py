from pydantic import BaseModel
from typing import Literal

class CreateGameRequest(BaseModel):
    host_id: int
    description: str
    location: str
    duration: int
    size: Literal[3, 4, 5]

class JoinGameRequest(BaseModel):
    user_id: int