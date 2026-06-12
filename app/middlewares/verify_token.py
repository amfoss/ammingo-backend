from fastapi import HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware
import os
from datetime import datetime
from app.routes.auth import generate_access_token
from app.db.models import User
from app.db.db import get_db
from sqlalchemy import select

secret = os.environ.get(
    "JWT_SECRET", default="dkjfaidfjei4ou9028ruq208mxuHHDUFGHjfeu9!#@*u9fj"
)
algorithm = os.environ.get("HASH_ALGORITHM", default="HS256")


async def verify_token(request, call_next):
    if request.url.path.startswith("/api/login/"):
        return await call_next(request)
    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    payload = jwt.decode(token, secret, algorithms=[algorithm])
    user_id = payload["user_id"]
    exp = payload["exp"]
    query = select(User).where(User.id == user_id)
    db = next(get_db())
    try:
        request.state.db = db
        user = db.execute(query).scalars().first()
        if not user:
            return JSONResponse(status_code=403, content={"error": "Unauthorized"})
        if datetime.fromtimestamp(exp) > datetime.now():
            token = generate_access_token(user_id)
            response = await call_next(request)
            response.set_cookie(
                key="access_token", value=token, httponly=True, secure=True
            )
            return response
        return await call_next(request)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
