from fastapi import Request, Response, APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from jose import jwt
import os
from datetime import datetime, timedelta
from app.routes.auth import generate_access_token
from app.db.db import get_db
from app.db.models import User
from sqlalchemy import select

secret = os.environ.get(
    "JWT_SECRET", default="dkjfaidfjei4ou9028ruq208mxuHHDUFGHjfeu9!#@*u9fj"
)
algorithm = os.environ.get("HASH_ALGORITHM", default="HS256")

router = APIRouter()


@router.middleware("http")
async def verify_token(
    request: Request, response: Response, call_next, db: Session = Depends(get_db)
):
    print("Called")
    if request.url.path.startswith("/api/login/"):
        call_next(request)
    token = request.cookie.get("access_token")
    if not token:
        print("No token")
        raise HTTPException(detail="Unauthorised", status_code=403)
    print(token)
    payload = jwt.decode(token, secret, all)
    user_id = payload["user_id"]
    exp = payload["exp"]
    query = select(User).where(User.id == id)
    user = db.execute(query).scalars().first()
    if not user:
        raise HTTPException(detail="Unknown user", status_code=403)
    if timedelta(exp) > datetime.now():
        print("Renewing token")
        token = generate_access_token(user_id)
        response.set_cookie(key="access_token", value=token, httponly=True, secure=True)
    call_next(response)
