from fastapi import APIRouter, Depends, status
from fastapi.exceptions import RequestValidationError
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from ..models import UserCreate, UserResponse, User, UserProfileResponse, Membership, Organization, OrganizationWorkspaceInfo
from ..database import sync_session, async_session
from ..core.security import hash_password
from ..dependencies import get_current_user, oauth2_scheme


router = APIRouter(tags=["Users"])

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


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    token: Annotated[str, Depends(oauth2_scheme)], 
    session: AsyncSession = Depends(async_session)
):
    statement = select(User)
    results = await session.execute(statement)
    return results.scalars().all()



@router.get("/users/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(async_session)
):
    """
    Fetch the currently authenticated user's profile metadata 
    along with their multi-tenant organization workspaces.
    """
    statement = (
        select(Organization, Membership.role, Membership.created_at)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == current_user.id)
    )
    
    result = await session.execute(statement)
    rows = result.all()  
    
    org_list = [
        OrganizationWorkspaceInfo(
            id=org.id,
            name=org.name,
            role=role,
            joined_at=joined_at
        )
        for org, role, joined_at in rows
    ]
    
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
        organizations=org_list
    )
