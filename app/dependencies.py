from fastapi import Header, Depends, HTTPException, status
from sqlmodel import Session, select
from fastapi.security import OAuth2PasswordBearer
import jwt
import os
import magic
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession


from .models import User, Membership, UserRole
from .database import async_session
from .core.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

MAX_FILE_SIZE = 5 * 1024 *1024
ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "text/plain": [".txt"]
}

async def validated_uploaded_file(file: UploadFile) -> UploadFile:
    filename = file.filename or ""
    file_extension = os.path.splitext(filename)[1].lower()

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    await file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail = f"File too large. Maximum size allowed is {MAX_FILE_SIZE}"
        )
    
    header_bytes = await file.read(2048)
    await file.seek(0)

    detected_mime = magic.from_buffer(header_bytes, mime = True)

    if detected_mime.startswith("text/") and file_extension == ".txt":
        detected_mime = "text/plain"

    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail = f"Unsupported file type: {detected_mime}. Allowed types: {','.join(ALLOWED_MIME_TYPES.keys())}"
        )

    if file_extension not in ALLOWED_MIME_TYPES[detected_mime]:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = f"File extension '{file_extension}' does not match the actual content_type ({detected_mime})"
        )

    return file

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(async_session)
) -> User:
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM])
        
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
            
        user_id = int(user_id_str)
        
    except (InvalidTokenError, ValueError):
        raise credentials_exception

    user = await session.get(User, user_id)
    if user is None:
        raise credentials_exception
        
    return user



class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(self,
        x_organization_id: int = Header(alias="X-Organization-ID"),
        current_user: User = Depends(get_current_user),
        session: Session = Depends(async_session)) -> User:
        
        statement = select(Membership).where(
            Membership.organization_id == x_organization_id,
            Membership.user_id == current_user.id
        )
        result = await session.execute(statement)
        membership = result.scalar_one_or_none()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not belong to this organization workspace.")
            
        if membership.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions tier insufficient for this workspace action.")
            
        return current_user
