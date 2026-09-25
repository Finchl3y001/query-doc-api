import jwt
from jwt.exceptions import InvalidTokenError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Depends, HTTPException, status
from sqlmodel import select, Session
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone
from typing import Annotated

from ..database import sync_session
from ..routers import users
from ..models import User
from ..config import Settings, get_settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

pass_hash = PasswordHash.recommended()

def hash_password(password: str):
    return pass_hash.hash(password)

def verify_password(plain_pwd: str, hashed_pwd: str):
    return pass_hash.verify(plain_pwd, hashed_pwd)


def create_access_token(data: dict, settings: Settings):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict, settings:Settings):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    return jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)

