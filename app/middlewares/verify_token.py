from fastapi import Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from jose import jwt
import os
from datetime import datetime, timezone
from app.routes.auth import generate_access_token
from app.db.models import User
from app.db.db import SessionLocal, get_db

secret = os.environ.get(
    "JWT_SECRET", default="dkjfaidfjei4ou9028ruq208mxuHHDUFGHjfeu9!#@*u9fj"
)
algorithm = os.environ.get("HASH_ALGORITHM", default="HS256")
EXCLUDED_PREFIXES = ("/api/login/", "/docs", "/redoc", "/openapi.json", "/uploads")


async def verify_token(request, call_next):
    is_public_game_get = (
        request.method == "GET"
        and request.url.path.startswith("/api/games/")
        and not request.url.path.endswith("/board/")
    )
    if request.url.path.startswith(EXCLUDED_PREFIXES) or is_public_game_get:
        return await call_next(request)
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    db = None
    try:
        try:
            payload = jwt.decode(token, secret, algorithms=[algorithm])
            expired = False
        except jwt.ExpiredSignatureError:
            payload = jwt.decode(
                token, secret, algorithms=[algorithm], options={"verify_exp": False}
            )
            expired = True
        user_id = payload["user_id"]
        query = select(User).where(User.id == user_id)
        db = SessionLocal()
        request.state.db = db
        user = db.execute(query).scalars().first()
        if not user:
            return JSONResponse(status_code=403, content={"error": "Unauthorized"})
        if expired:
            token = generate_access_token(user_id)
        response = await call_next(request)
        response.set_cookie(key="access_token", value=token, httponly=True, secure=True)
        return response
    except Exception as e:
        return JSONResponse(
            status_code=403, content={"error": f"Unauthorized: {str(e)}"}
        )
    finally:
        if db is not None:
            db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")

    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        user_id = payload.get("user_id")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
