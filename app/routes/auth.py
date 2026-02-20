from app.db.models import User
from app.db.db import get_db
from app.models.auth import UserDetails
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from email.message import EmailMessage
import jwt
import os
import dotenv
import random
import string
import smtplib
from datetime import datetime, timezone, timedelta

dotenv.load_dotenv()
router = APIRouter()

secret=os.environ.get("JWT_SECRET", default="dkjfaidfjei4ou9028ruq208mxuHHDUFGHjfeu9!#@*u9fj")
algorithm=os.environ.get("HASH_ALGORITHM", default="SHA256")
expiry_time=int(os.environ.get("TOKEN_EXPIRY_TIME", default="1"))
email_addr = os.environ.get("EMAIL_ADDRESS")
email_pass = os.environ.get("EMAIL_PASSWORD")
smtp_server = os.environ.get("SMTP_SERVER")
smtp_port = os.environ.get("SMTP_PORT")
email_otp = {}

def generate_access_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(hours=expiry_time)
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
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

@router.get("/login/email/")
def login_email(email: str, db: Session = Depends(get_db)):
    query = select(User).where(User.email==email)
    user = db.execute(query)
    if not user:
        raise HTTPException(detail="No user found", status_code=404)
    otp_code = ''.join(random.choices(string.digits, k=6))

    send_mail(email, otp_code)
    email_otp[email] = otp_code
    return {'Sucess': 'Sent the verification mail'}

@router.get("/login/verify-otp", response_model=UserDetails)
def verify_otp(otp: str, email: str, db: Session = Depends(get_db)):
    actual_otp = email_otp[email]
    if otp!=actual_otp:
        raise HTTPException(detail="Incorrect OTP", status_code=401)
    
    query = select(User).where(email==email) # Fetch user using email from request
    user = db.execute(query)
    return user