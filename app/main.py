from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth
from app.routes import game

from app.db.db import engine, Base
from app.db import models  



app = FastAPI(title="amMingo")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["users"])
app.include_router(game.router, prefix="/api", tags=["games"])

@app.get('/')
def root():
    return {'amMingo': 'This is amMingo'}