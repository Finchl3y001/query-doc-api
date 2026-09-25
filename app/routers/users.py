from fastapi import FastAPI, Depends, status, APIRouter, HTTPException, Response, Cookie
from sqlmodel import SQLModel, Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import UserCreate, UserResponse, User, TokenResponse
from ..database import sync_session, async_session
from pwdlib import PasswordHash
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlalchemy.exc import IntegrityError
from ..core.security import hash_password, verify_password, create_access_token, oauth2_scheme, create_refresh_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated, Dict
from ..config import Settings, get_settings


router =APIRouter(tags=["Users"])


@router.post("/users", response_model=UserResponse)
def register_user(user: UserCreate, session: Session = Depends(sync_session)):
        statement = select(User).where((User.email == user.email) | (User.username == user.username))
        existing_user = session.exec(statement).first()

        if existing_user:
            field = "email" if existing_user.email == user.email else "username"
            value = user.email if field == "email" else user.username

            raise RequestValidationError([
                {
                    "loc" : ("body", field),
                    "msg" : f"The {field} '{value}' is already taken",
                    "type": "value_error.already_exists"
                }
            ])
        db_user = User.model_validate(user)
        db_user.password = hash_password(user.password)

        session.add(db_user)
        session.commit()
        session.refresh(db_user)

        return db_user


@router.post("/login", response_model = TokenResponse)
def login(
    response: Response, 
    settings: Annotated[Settings, Depends(get_settings)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    session: Session = Depends(sync_session) ):
    
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Incorrect username or password",
        headers = {"WWW-Authenticate": "Bearer"}
    )
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user:
        raise credentials_exception
    
    valid_pass = verify_password(form_data.password, user.password)
    if not valid_pass:
        raise credentials_exception

    user_data = {"sub": user.username}

    access_token = create_access_token(user_data, settings)
    refresh_token = create_refresh_token(user_data, settings)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,        
        secure=True,          
        samesite="lax",       
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, 
    )

    return {
        "access_token" : access_token,
        "token_type" : "bearer"
    }


@router.post("/token/refresh")
def refresh_access_token(settings: Annotated[Settings, Depends(get_settings)], refresh_token: str = Cookie(None)) -> Dict[str, str]:
    """
    Refresh endpoint.
    Extracts the refresh token from the secure cookie, validates it,
    and returns a brand-new short-lived access token.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing from cookies"
        )
        
    try:
        payload = jwt.decode(refresh_token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM])

        if payload.get("type") != 'refresh':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token type"
            )

        username = payload.get("sub")

        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token payload"
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again."
        )

    new_access_token = create_access_token(data={"sub": username})
    
    return {"access_token": new_access_token, "token_type": "bearer"}



@router.get("/users", response_model=list[UserResponse])
async def get_users(token: Annotated[str, Depends(oauth2_scheme)], session : AsyncSession = Depends(async_session)):
    statement = select(User)
    results = await session.execute(statement)
    user_results = results.scalars().all()
    
    return user_results