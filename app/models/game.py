from pydantic import BaseModel
from typing import Literal


class CreateGameRequest(BaseModel):
    host_id: int
    description: str
    location: str
    duration: int


class StartGameRequest(BaseModel):
    user_id: int
    size: int


class JoinGameRequest(BaseModel):
    user_id: int


class CreateGameResponse(BaseModel):
    game_id: int
    join_code: str
    qr_img: str


class JoinGameResponse(BaseModel):
    message: str
    game_id: int
    user_id: int


class LobbyResponse(BaseModel):
    player_count: int
    players: list[str]
    available_board_sizes: list[Literal[3, 4, 5]]


class StartGameResponse(BaseModel):
    message: str
    board_size: Literal[3, 4, 5]
