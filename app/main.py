from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth
from app.routes import game
from app.routes import profile
from app.db.db import engine, Base
from starlette.middleware.sessions import SessionMiddleware
from app.middlewares.verify_token import verify_token
import os
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="amMingo", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware, same_site="lax", secret_key=os.getenv("JWT_SECRET")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(verify_token)

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(game.router, prefix="/api", tags=["games"])
app.include_router(profile.router, prefix="/api", tags=["profile"])


@app.get("/")
def root():
    return {"amMingo": "This is amMingo"}
