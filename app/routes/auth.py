from app.db.models import User
from app.db.db import get_db
from app.models.auth import UserDetails, EmailLoginRequest, EmailVerify
from fastapi import FastAPI, HTTPException, Depends, Request, Response, responses
from sqlalchemy import select
from sqlalchemy.orm import Session
from email.message import EmailMessage
from jose import jwt
import os
from authlib.integrations.starlette_client import OAuth
import dotenv
import random
import string
import smtplib
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timezone, timedelta

secret = os.environ.get(
    "JWT_SECRET", default="dkjfaidfjei4ou9028ruq208mxuHHDUFGHjfeu9!#@*u9fj"
)
algorithm = os.environ.get("HASH_ALGORITHM", default="HS256")
expiry_time = int(os.environ.get("TOKEN_EXPIRY_TIME", default="1"))
email_addr = os.environ.get("EMAIL_ADDRESS")
email_pass = os.environ.get("EMAIL_PASSWORD")
smtp_server = os.environ.get("SMTP_SERVER")
smtp_port = os.environ.get("SMTP_PORT")
google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
frontend_url = os.environ.get("FRONTEND_URL")

dotenv.load_dotenv()
auth_app = FastAPI()
oauth = OAuth()
oauth.register(
    name="google",
    client_id=google_client_id,
    client_secret=google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
auth_app.add_middleware(
    SessionMiddleware, same_site="lax", secret_key=os.getenv("JWT_SECRET")
)

otps = {}  # For storing otp while logging in


def generate_access_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds1=expiry_time),
    }
    token = jwt.encode(payload, secret, algorithm)
    return token


def send_mail(to_email, otp):
    msg = EmailMessage()
    msg["Subject"] = "Your OTP Verification Code"
    msg["From"] = email_addr
    msg["To"] = to_email
    msg.set_content(f"Your OTP is: {otp}\n\nThis OTP is valid for 5 minutes.")

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(email_addr, email_pass)
            smtp.send_message(msg)
            smtp.quit()
            return 1
    except Exception:
        return 0


@auth_app.post("/login/email")
def login_email(payload: EmailLoginRequest, db: Session = Depends(get_db)):
    email = payload.email
    query = select(User).where(User.email == email)
    user = db.execute(query).scalars().first()
    if not user:
        index = email.find("@")
        username = email[:index]
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        user = User(username=username, name=username, email=email, code=code)
        db.add(user)
        db.commit()
        db.refresh(user)
    otp_code = "".join(random.choices(string.digits, k=6))
    sent = send_mail(to_email=email, otp=otp_code)
    if not sent:
        raise HTTPException(f"Failed to send email to {email}")
    otps[email] = {"exp": datetime.now() + timedelta(minutes=5), "otp_code": otp_code}
    return {"Sucess": "Sent the verification mail"}


@auth_app.post("/login/verify-otp", response_model=UserDetails)
def verify_otp(
    payload: EmailVerify, response: Response, db: Session = Depends(get_db)
) -> UserDetails:
    email = payload.email
    otp = payload.otp
    actual_otp = otps[email]["otp_code"]
    if datetime.now() > otp[email]["exp"]:
        raise HTTPException(detail="OTP Expired", status_code=403)
    if otp != actual_otp:
        raise HTTPException(detail="Incorrect OTP", status_code=401)

    query = select(User).where(
        User.email == email
    )  # Fetch user using email from request
    user = db.execute(query).scalars().first()
    token = generate_access_token(user.id)
    response.set_cookie(key="access_token", value=token, httponly=True, secure=True)
    return user


@auth_app.get("/login/oauth")
async def redirect_to_google(request: Request):
    redirect = request.url_for("oauth_callback")
    return await oauth.google.authorize_redirect(request, redirect)


@auth_app.get("/login/callback", name="oauth_callback")
async def callback(
    request: Request, db: Session = Depends(get_db)
) -> UserDetails:
    token = await oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]
    query = select(User).where(User.email == token["userinfo"]["email"])
    user = db.execute(query).scalars().first()
    if not user:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        user = User(
            username=f"user_{userinfo['sub'][-8:]}",
            name=userinfo["name"],
            email=userinfo["email"],
            code=code,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = generate_access_token(user_id=user.id)
    response = responses.RedirectResponse(url=frontend_url, status_code=302)
    response.set_cookie(
        key="access_token", value=access_token, httponly=True, secure=True
    )

    return response
