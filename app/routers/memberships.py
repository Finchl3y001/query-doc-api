from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlmodel import Session, select

from ..database import sync_session
from ..dependencies import RoleChecker
from ..models import (
    Membership,
    MembershipCreate,
    MembershipResponse,
    MembershipUpdate,
    User,
    UserRole,
)

router = APIRouter(prefix="/memberships", tags=["Memberships"])


@router.get("", response_model=list[MembershipResponse])
def get_organization_members(
    # FIX 1: Enforce multi-tenant tracking via the organizational header
    x_organization_id: int = Header(alias="X-Organization-ID"),
    # FIX 2: Restrict viewing membership lists to active authenticated workspace users
    current_user: User = Depends(
        RoleChecker(
            [
                UserRole.SUPER_ADMIN,
                UserRole.ADMIN,
                UserRole.MANAGER,
                UserRole.MEMBER,
            ]
        )
    ),
    session: Session = Depends(sync_session),
):
    statement = select(Membership).where(
        Membership.organization_id == x_organization_id
    )
    results = session.exec(statement).all()
    return results


@router.post("", response_model=MembershipResponse)
def add_user_to_organization(
    membership: MembershipCreate,
    x_organization_id: int = Header(alias="X-Organization-ID"),

    current_user: User = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER])),
    session: Session = Depends(sync_session),
):
    membership.organization_id = x_organization_id

    user = session.get(User, membership.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target User ID does not exist",
        )

    statement = select(Membership).where(
        Membership.user_id == membership.user_id,
        Membership.organization_id == x_organization_id,
    )
    existing_membership = session.exec(statement).first()
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The assigned membership already exists for this organization",
        )

    try:
        validated_role = UserRole(membership.role)
    except ValueError:
        valid_options = ", ".join([r.value for r in UserRole])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assignment role. Choose from: {valid_options}",
        )

    db_membership = Membership(
        user_id=membership.user_id,
        organization_id=x_organization_id,
        role=validated_role,
    )
    session.add(db_membership)
    session.commit()
    session.refresh(db_membership)

    return db_membership


@router.patch("/{membership_id}", response_model=MembershipResponse)
def update_membership_role(
    membership_id: int,
    payload: MembershipUpdate,
    x_organization_id: int = Header(alias="X-Organization-ID"),
    current_user: User = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER])),
    session: Session = Depends(sync_session),
):
    db_membership = session.get(Membership, membership_id)
    if (
        not db_membership
        or db_membership.organization_id != x_organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership record not found within this workspace",
        )

    if payload.role is not None:
        try:
            db_membership.role = UserRole(payload.role)
        except ValueError:
            valid_options = ", ".join([r.value for r in UserRole])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role update value. Choose from: {valid_options}",
            )

    if (
        db_membership.role == UserRole.ADMIN
        and current_user.role != UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only top-tier workspace Administrators can modify other Admin profiles",
        )

    session.add(db_membership)
    session.commit()
    session.refresh(db_membership)
    return db_membership


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_from_organization(
    membership_id: int,
    x_organization_id: int = Header(alias="X-Organization-ID"),
    current_user: User = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER])),
    session: Session = Depends(sync_session),
):
    db_membership = session.get(Membership, membership_id)
    if (
        not db_membership
        or db_membership.organization_id != x_organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership record not found within this workspace",
        )

    if db_membership.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-removal blocks triggered. You cannot delete your own profile membership from the inside.",
        )

    session.delete(db_membership)
    session.commit()
