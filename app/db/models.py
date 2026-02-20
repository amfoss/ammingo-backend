from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.db import Base
from datetime import datetime, timezone


class User(Base):
    __tablename__="user"
    id=Column(Integer, primary_key=True)
    username=Column(String, unique=True, nullable=False)
    name=Column(String, nullable=False)
    email=Column(String, unique=True)
    code=Column(String, unique=True, nullable=False)

    game_user_bingos = relationship("GameUserBingo", back_populates="user")

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

    size = Column(Integer, nullable=False)

    qr_img = Column(Text, nullable=True)

    game_user_bingos = relationship("GameUserBingo", back_populates="game")
    

class Bingo(Base):
    __tablename__="bingo"
    id=Column(Integer, primary_key=True)
    row=Column(Integer, nullable=False)
    col=Column(Integer, nullable=False)
    bingo_char=Column(String, nullable=False)
    image_link=Column(String, unique=True)
    game_user_bingos = relationship("GameUserBingo", back_populates="bingo")

class GameUserBingo(Base):
    __tablename__ = "game_user_bingo"

    game_id = Column(ForeignKey("game.id"), primary_key=True)
    user_id = Column(ForeignKey("user.id"), primary_key=True)
    bingo_id = Column(ForeignKey("bingo.id"), primary_key=True)
    points = Column(Integer, default=0)

    game = relationship("Game", back_populates="game_user_bingos")
    user = relationship("User", back_populates="game_user_bingos")
    bingo = relationship("Bingo", back_populates="game_user_bingos")
