from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from app.db.db import Base
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    profile_image = Column(String, nullable=True, default="uploads/default.png")

    game_user_bingo = relationship("Bingo", back_populates="user")


class Game(Base):
    __tablename__ = "game"
    __table_args__ = (
        CheckConstraint("start_time < end_time", name="check_valid_time"),
    )

    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    winner_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(255), nullable=False)
    code = Column(String(6), unique=True, nullable=False)
    board_size = Column(Integer, nullable=True)
    qr_img = Column(Text, nullable=True)

    game_user_bingo = relationship("Bingo", back_populates="game")


class BingoTiles(Base):
    __tablename__ = "bingo_tiles"

    id = Column(Integer, primary_key=True)
    row = Column(Integer, nullable=False)
    col = Column(Integer, nullable=False)
    bingo_char = Column(String, nullable=False)
    bingo_id = Column(Integer, ForeignKey("bingo.id"))
    image_url = Column(String, unique=True)

    game_user_bingo = relationship("Bingo", back_populates="bingo_tiles")


class Bingo(Base):
    __tablename__ = "bingo"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("game.id"))
    user_id = Column(Integer, ForeignKey("user.id"))
    points = Column(Integer, default=0)

    game = relationship("Game", back_populates="game_user_bingo")
    user = relationship("User", back_populates="game_user_bingo")
    bingo_tiles = relationship("BingoTiles", back_populates="game_user_bingo")
