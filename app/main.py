from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.auth import auth_app
from app.routes import game
from app.routes import profile  
from app.db.db import engine, Base
from app.middlewares.verify_token import VerifyToken
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="amMingo", lifespan=lifespan)

app.add_middleware(VerifyToken)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/api/", auth_app)
app.include_router(game.router, prefix="/api", tags=["games"])
app.include_router(profile.router, prefix="/api", tags=["profile"])  


@app.get("/")
def root():
    return {"amMingo": "This is amMingo"}