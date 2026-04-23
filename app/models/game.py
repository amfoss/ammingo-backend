from pydantic import BaseModel
from typing import Literal
from datetime import datetime


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


class GameDetailResponse(BaseModel):
    game_id: int
    host_id: int
    description: str
    location: str
    start_time: datetime
    end_time: datetime
    code: str
    board_size: int | None
    qr_img: str | None

class TileResponse(BaseModel):
    id: int
    row: int
    col: int
    bingo_char: str

class BingoBoardResponse(BaseModel):
    bingo_id: int
    user_id: int
    game_id: int
    points: int
    tiles: list[TileResponse]