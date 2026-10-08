from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from ..core.config import Settings, get_settings
from ..core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from ..database import sync_session
from ..dependencies import get_current_user
from ..models import TokenResponse, User, UserCreate, UserResponse

router = APIRouter(tags=["Authentication"])

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, session: Session = Depends(sync_session)):
    statement = select(User).where((User.email == user.email) | (User.username == user.username))
    existing_user = session.exec(statement).first()

    if existing_user:
        field = "email" if existing_user.email == user.email else "username"
        value = user.email if field == "email" else user.username

        raise RequestValidationError([
            {
                "loc": ("body", field),
                "msg": f"The {field} '{value}' is already taken",
                "type": "value_error.already_exists"
            }
        ])
        
    db_user = User.model_validate(user)
    db_user.password = hash_password(user.password)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


@router.post("/login", response_model=TokenResponse)
def login(
    response: Response, 
    settings: Annotated[Settings, Depends(get_settings)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    session: Session = Depends(sync_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.password):
        raise credentials_exception

    #user_data = {"sub": user.username}
    user_data = {"sub": str(user.id)}

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

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token/refresh")
def refresh_access_token(
    settings: Annotated[Settings, Depends(get_settings)], 
    refresh_token: str = Cookie(None)
) -> dict[str, str]:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing from cookies"
        )
        
    try:
        payload = jwt.decode(refresh_token, settings.REFRESH_SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM])
        if payload.get("type") != 'refresh' or payload.get("sub") is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    new_access_token = create_access_token(data={"sub": payload.get("sub")}, settings=settings)
    
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout", status_code = status.HTTP_200_OK)
def logout(
    response: Response,
    current_user: User = Depends(get_current_user)):

    response.delete_cookie(
        key="refresh_token",
        path='/',
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    return {"detail": "Succesfully logged out. Session cleared."}
