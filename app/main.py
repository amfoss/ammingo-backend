from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth
from app.routes import game
from app.db.db import engine, Base
from app.middlewares.verify_token import VerifyToken
from starlette.middleware.sessions import SessionMiddleware
import os
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="amMingo", lifespan=lifespan)

auth.router.add_middleware(
    SessionMiddleware, same_site="lax", secret_key=os.getenv("JWT_SECRET")
)

app.add_middleware(VerifyToken)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(game.router, prefix="/api", tags=["games"])


@app.get("/")
def root():
    return {"amMingo": "This is amMingo"}
