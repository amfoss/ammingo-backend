from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

import secrets
import string
import qrcode
from io import BytesIO
import base64
import os
import uuid
import shutil

from app.db.db import get_db
from app.middlewares.verify_token import get_current_user
from app.db.models import Game, Bingo, User, BingoTiles

from datetime import datetime, timedelta, timezone
from app.models.game import (
    CreateGameRequest,
    StartGameRequest,
    CreateGameResponse,
    JoinGameResponse,
    LobbyResponse,
    StartGameResponse,
    GameDetailResponse,
    BingoBoardResponse,
    TileResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    TileSubmit,
    GameStatusResponse,
)
import random

router = APIRouter()
UPLOAD_DIR = "uploads/"


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
def create_game(
    data: CreateGameRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    code = create_unique_code(db)
    qr_img = generate_qr_base64(code)
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(minutes=data.duration)

    new_game = Game(
        host_id=current_user.id,
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
def join_game(
    code: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):

    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    existing = (
        db.query(Bingo).filter_by(game_id=game.id, user_id=current_user.id).first()
    )

    if existing:
        return {
            "message": "User already joined",
            "game_id": game.id,
            "username": current_user.username,
        }

    if game.board_size is not None:
        raise HTTPException(status_code=400, detail="Game already started")

    board = Bingo(game_id=game.id, user_id=current_user.id)

    db.add(board)
    db.commit()

    return {
        "message": "Joined successfully",
        "game_id": game.id,
        "username": current_user.username,
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

    total_players = len(player_names)
    if total_players > 25:
        available_sizes = [5]
    elif total_players > 16:
        available_sizes = [4, 5]
    elif total_players > 9:
        available_sizes = [3, 4]
    else:
        available_sizes = [3]

    return {
        "player_count": total_players,
        "players": player_names,
        "available_board_sizes": available_sizes,
    }


@router.post("/games/{code}/start", response_model=StartGameResponse)
def start_game(
    code: str,
    data: StartGameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if current_user.id != game.host_id:
        raise HTTPException(status_code=403, detail="Only host can start the game")

    if game.board_size is not None:
        raise HTTPException(status_code=400, detail="Game already started")

    participants = db.query(Bingo).filter(Bingo.game_id == game.id).all()
    total_players = len(participants)

    if total_players > 25:
        allowed = [5]
    elif total_players > 16:
        allowed = [4, 5]
    elif total_players > 9:
        allowed = [3, 4]
    else:
        allowed = [3]

    if data.size not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Board size {data.size}x{data.size} is not allowed for {total_players} players. Allowed: {allowed}",
        )

    game.board_size = data.size

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

    if not other_players:
        raise HTTPException(
            status_code=400,
            detail="Not enough players to start the game. You need at least 2 players.",
        )

    if len(other_players) >= total_tiles:
        random.shuffle(other_players)
        selected_players = other_players[:total_tiles]
    else:
        # Sample with replacement if there are fewer players than board tiles
        selected_players = random.choices(other_players, k=total_tiles)

    # Collect start characters from selected players
    unique_start_letters = {
        p.name.strip()[0].upper() for p in selected_players if p.name.strip()
    }

    # If starting letters diversity is low (less than 3 unique letters),
    # generate random letters from the alphabet A-Z to populate the board tiles.
    if len(unique_start_letters) < 3:
        tile_chars = [random.choice(string.ascii_uppercase) for _ in range(total_tiles)]
    else:
        tile_chars = [p.name.strip()[0].upper() for p in selected_players]
        random.shuffle(tile_chars)

    for i, char in enumerate(tile_chars):
        new_tile = BingoTiles(
            row=i // size,
            col=i % size,
            bingo_char=char,
            bingo_id=board.id,
        )
        db.add(new_tile)


@router.get("/games/{code}", response_model=GameDetailResponse)
def get_game_details(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    game = db.query(Game).filter(Game.code == code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    host = db.query(User).filter(User.id == game.host_id).first()
    host_name = host.name if host else "Unknown Host"
    host_pfp = host.profile_image if host else "/uploads/default.png"

    return GameDetailResponse(
        game_id=game.id,
        host_name=host_name,
        host_pfp=host_pfp,
        description=game.description,
        location=game.location,
        start_time=game.start_time,
        end_time=game.end_time,
        code=game.code,
        board_size=game.board_size,
        qr_img=f"data:image/png;base64,{game.qr_img}" if game.qr_img else None,
    )


@router.get("/games/{code}/board/", response_model=BingoBoardResponse)
def get_user_board(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    game = db.query(Game).filter(Game.code == code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    board = db.query(Bingo).filter_by(game_id=game.id, user_id=current_user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    tiles = (
        db.query(BingoTiles)
        .filter(BingoTiles.bingo_id == board.id)
        .order_by(BingoTiles.row, BingoTiles.col)
        .all()
    )

    return BingoBoardResponse(
        bingo_id=board.id,
        username=current_user.username,
        game_id=board.game_id,
        points=board.points,
        tiles=[
            TileResponse(
                id=tile.id,
                row=tile.row,
                col=tile.col,
                bingo_char=tile.bingo_char,
                image_url=tile.image_url,
            )
            for tile in tiles
        ],
    )


@router.get("/games/{code}/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(code: str, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.code == code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    results = (
        db.query(User.code, User.name, User.username, Bingo.points)
        .join(Bingo, Bingo.user_id == User.id)
        .filter(Bingo.game_id == game.id)
        .order_by(Bingo.points.desc())
        .all()
    )

    leaderboard = [
        LeaderboardEntry(code=r.code, name=r.name, username=r.username, points=r.points)
        for r in results
    ]

    return LeaderboardResponse(leaderboard=leaderboard)


@router.get("/games/{code}/status", response_model=GameStatusResponse)
def get_game_status(code: str, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.code == code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Get all boards for this game
    boards = db.query(Bingo).filter(Bingo.game_id == game.id).all()
    board_ids = [b.id for b in boards]

    # Calculate tiles_done (tiles where image_url is set)
    tiles_done = 0
    if board_ids:
        tiles_done = (
            db.query(BingoTiles)
            .filter(
                BingoTiles.bingo_id.in_(board_ids), BingoTiles.image_url.isnot(None)
            )
            .count()
        )

    active_players = len(boards)
    max_cap = 100

    return GameStatusResponse(
        tiles_done=tiles_done, active_players=active_players, max_cap=max_cap
    )


@router.post("/games/tile-submit", response_model=TileSubmit)
def tile_submit(
    bingo_id: int = Form(...),
    row: int = Form(...),
    col: int = Form(...),
    friend_name: str = Form(...),
    friend_code: str = Form(...),
    fact: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):  # you can submit same guy multiple times
    friend = db.query(User).filter(User.code == friend_code.strip().upper()).first()
    if not friend or (
        friend.name.strip().lower() != friend_name.strip().lower()
        and friend.username.strip().lower() != friend_name.strip().lower()
    ):
        raise HTTPException(status_code=404, detail="Friend not found or code mismatch")
    bingo = db.query(Bingo).filter(Bingo.id == bingo_id).first()
    if not bingo:
        raise HTTPException(status_code=404, detail="Bingo board not found")

    friend_in_game = (
        db.query(Bingo)
        .filter(Bingo.game_id == bingo.game_id, Bingo.user_id == friend.id)
        .first()
    )
    friend_already_submitted = db.query(BingoTiles).filter(
        BingoTiles.friend_id == friend.id, BingoTiles.bingo_id == bingo.id
    )

    if not friend_in_game:
        raise HTTPException(status_code=400, detail="Friend is not part of this game")
    if friend_already_submitted:
        raise HTTPException(status_code=400, detail="Friend has already been submitted")

    tile = (
        db.query(BingoTiles)
        .filter(
            BingoTiles.bingo_id == bingo_id,
            BingoTiles.row == row,
            BingoTiles.col == col,
        )
        .first()
    )
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")
    if tile.image_url:
        raise HTTPException(status_code=400, detail="Tile already submitted")

    if friend.name.strip()[0].upper() != tile.bingo_char:
        raise HTTPException(
            status_code=400, detail=f"Friend's name must start with {tile.bingo_char}"
        )

    ext = os.path.splitext(image.filename)[-1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    tile.image_url = filepath
    tile.random_fact = fact
    db.commit()
    db.refresh(tile)

    n = bingo.game.board_size
    submitted = {
        (i.row, i.col)
        for i in db.query(BingoTiles).filter(BingoTiles.bingo_id == bingo_id).all()
        if i.image_url
    }

    points = 0

    if all((row, c) in submitted for c in range(n)):
        points += 500

    if all((r, col) in submitted for r in range(n)):
        points += 500

    if row == col and all((i, i) in submitted for i in range(n)):
        points += 500
    if row + col == n - 1 and all((i, n - 1 - i) in submitted for i in range(n)):
        points += 500

    points = points if points > 0 else 100
    bingo.points += points
    db.commit()

    return tile
