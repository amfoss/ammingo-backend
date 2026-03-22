from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import secrets
import string
import qrcode
from io import BytesIO
import base64
import os

from app.db.db import get_db
from app.db.models import Game, Bingo, User, BingoTiles

from datetime import datetime, timedelta, timezone
from app.models.game import (
    CreateGameRequest,
    JoinGameRequest,
    StartGameRequest,
    CreateGameResponse,
    JoinGameResponse,
    LobbyResponse,
    StartGameResponse,
)
import random

router = APIRouter()


def generate_game_code():
    characters = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(characters) for _ in range(6))


def create_unique_code(db: Session):
    while True:
        code = generate_game_code()
        existing = db.query(Game).filter(Game.code == code).first()
        if not existing:
            return code


def generate_qr_base64(code: str):
    BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    join_url = f"{BASE_URL}/api/games/join/{code}"

    qr = qrcode.make(join_url)

    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode()


@router.post("/games", response_model=CreateGameResponse)
def create_game(data: CreateGameRequest, db: Session = Depends(get_db)):

    code = create_unique_code(db)
    qr_img = generate_qr_base64(code)
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(minutes=data.duration)

    new_game = Game(
        host_id=data.host_id,
        description=data.description,
        location=data.location,
        start_time=start_time,
        end_time=end_time,
        code=code,
        qr_img=qr_img,
    )

    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    return {
        "game_id": new_game.id,
        "join_code": new_game.code,
        "qr_img": f"data:image/png;base64,{new_game.qr_img}",
    }


@router.post("/games/join/{code}", response_model=JoinGameResponse)
def join_game(code: str, data: JoinGameRequest, db: Session = Depends(get_db)):

    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    existing = db.query(Bingo).filter_by(game_id=game.id, user_id=data.user_id).first()

    if existing:
        return {
            "message": "User already joined",
            "game_id": game.id,
            "user_id": data.user_id,
        }

    if game.board_size is not None:
        raise HTTPException(status_code=400, detail="Game already started")

    board = Bingo(game_id=game.id, user_id=data.user_id)

    db.add(board)
    db.commit()

    return {
        "message": "Joined successfully",
        "game_id": game.id,
        "user_id": data.user_id,
    }


@router.get("/games/{code}/lobby", response_model=LobbyResponse)
def get_lobby(code: str, db: Session = Depends(get_db)):

    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    players = (
        db.query(User.name)
        .join(Bingo, Bingo.user_id == User.id)
        .filter(Bingo.game_id == game.id)
        .all()
    )

    player_names = [p.name for p in players]

    return {
        "player_count": len(player_names),
        "players": player_names,
        "available_board_sizes": [3, 4, 5],
    }


@router.post("/games/{code}/start", response_model=StartGameResponse)
def start_game(code: str, data: StartGameRequest, db: Session = Depends(get_db)):

    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if data.user_id != game.host_id:
        raise HTTPException(status_code=403, detail="Only host can start the game")

    if game.board_size is not None:
        raise HTTPException(status_code=400, detail="Game already started")

    game.board_size = data.size

    participants = db.query(Bingo).filter(Bingo.game_id == game.id).all()

    for participant in participants:
        create_bingo_matrix(db, game, participant.user_id)

    db.commit()

    return {"message": "Game started", "board_size": data.size}


def create_bingo_matrix(db: Session, game: Game, user_id: int):

    board = db.query(Bingo).filter_by(game_id=game.id, user_id=user_id).first()

    if not board:
        raise HTTPException(status_code=404, detail="Board not found for user")

    size = game.board_size
    total_tiles = size * size


    other_players = (
        db.query(User)
        .join(Bingo, Bingo.user_id == User.id)
        .filter(Bingo.game_id == game.id)
        .filter(User.id != user_id)
        .all()
    )

    if len(other_players) < total_tiles:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough players to fill a {size}x{size} board"
        )

    random.shuffle(other_players)
    selected_players = other_players[:total_tiles]

    
    for i, player in enumerate(selected_players):
        new_tile = BingoTiles(
            row=i // size,
            col=i % size,
            bingo_char=player.name,
            bingo_id=board.id
        )
        db.add(new_tile)
