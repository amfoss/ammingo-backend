from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

import secrets
import string
import qrcode
from io import BytesIO
import base64
import os

from app.db.db import get_db
from app.db.models import Game, GameParticipant
from datetime import datetime, timedelta, timezone
from app.models.game import CreateGameRequest, JoinGameRequest


router = APIRouter()


def generate_game_code():
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(6))


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


@router.post("/games")
def create_game(
    data: CreateGameRequest,
    db: Session = Depends(get_db)
):


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
        size=data.size,
        code=code,
        qr_img=qr_img
    )

    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    return {
        "game_id": new_game.id,
        "join_code": new_game.code,
        "qr_img": f"data:image/png;base64,{new_game.qr_img}"
    }


@router.post("/games/join/{code}")
def join_game(
    code: str,
    data: JoinGameRequest,
    db: Session = Depends(get_db)
):
    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    existing = db.query(GameParticipant).filter_by(
        game_id=game.id,
        user_id=data.user_id
    ).first()

    if existing:
        return {"message": "User already joined"}

    participant = GameParticipant(
        game_id=game.id,
        user_id=data.user_id
    )

    db.add(participant)
    db.commit()

    return {
        "message": "Joined successfully",
        "game_id": game.id,
        "user_id": data.user_id
    }


