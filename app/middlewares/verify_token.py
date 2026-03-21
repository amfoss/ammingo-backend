from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt
import os
from datetime import datetime
from app.routes.auth import generate_access_token
from app.db.models import User
from app.db.db import SessionLocal

secret = os.environ.get(
    "JWT_SECRET", default="dkjfaidfjei4ou9028ruq208mxuHHDUFGHjfeu9!#@*u9fj"
)
algorithm = os.environ.get("HASH_ALGORITHM", default="HS256")
DATABASE_URL = os.getenv("DB_URL")


class VerifyToken(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next
    ):
        if "login" in request.url.path:
            response = await call_next(request)
            return response
        token = request.cookies.get("access_token")
        if not token:
            print("No token")
            return JSONResponse({"detail": "Unauthorized"}, status_code=status.HTTP_403_FORBIDDEN)
        # Get database
        db = SessionLocal()

        payload = jwt.decode(token, secret, [algorithm])
        user_id = payload["user_id"]
        exp = payload["exp"]
        query = select(User).where(User.id == user_id)
        user = db.execute(query).scalars().first()
        if not user:
            return JSONResponse({"detail": "Unknown user"}, status_code=403)
        exp_datetime = datetime.fromtimestamp(exp)
        if exp_datetime > datetime.now():
            token = generate_access_token(user_id)
        response = await call_next(request)
        response.set_cookies(key="access_token", value=token, httponly=True, secure=True)
        return response