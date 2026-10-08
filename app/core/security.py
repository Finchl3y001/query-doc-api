from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from ..core.config import Settings

pass_hash = PasswordHash.recommended()

def hash_password(password: str):
    return pass_hash.hash(password)

def verify_password(plain_pwd: str, hashed_pwd: str):
    return pass_hash.verify(plain_pwd, hashed_pwd)


def create_access_token(data: dict, settings: Settings):
    to_encode = data.copy()

    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})

    return jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict, settings:Settings):
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    return jwt.encode(to_encode, settings.REFRESH_SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)

