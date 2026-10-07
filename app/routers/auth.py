from typing import Annotated, Dict
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
import jwt

from ..models import User, TokenResponse
from ..database import sync_session
from ..core.config import Settings, get_settings
from ..core.security import verify_password, create_access_token, create_refresh_token
from ..dependencies import get_current_user


router = APIRouter(tags=["Authentication"])

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
) -> Dict[str, str]:
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
