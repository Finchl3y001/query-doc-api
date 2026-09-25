from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from ..database import sync_session
from ..models import Membership, MembershipCreate, MembershipResponse, MembershipUpdate, User, Organization

router = APIRouter(prefix="/memberships", tags=["Memberships"])

@router.get("/{org_id}", response_model=list[MembershipResponse])
def get_organization_members(org_id: int, session: Session = Depends(sync_session)):
    statement = select(Membership).where(Membership.organization_id == org_id)
    results = session.exec(statement).all()

    return results

@router.post("", response_model = MembershipResponse)
def add_user_to_organization(membership: MembershipCreate, session: Session = Depends(sync_session)):
    user = session.get(User, membership.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User ID does not exist")

    org = session.get(Organization, membership.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization ID does not exist")

    statement = select(Membership).where(Membership.user_id == membership.user_id, Membership.organization_id == membership.organization_id)
    existing_membership = session.exec(statement).first()
    if existing_membership:
        raise HTTPException(status_code=400, detail="The assigned membership already exists")
    
    allowed_roles = {"admin","user", "member"}
    if membership.role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role '{membership.role}': Valid roles are:admin, user or member")

   
    db_membership = Membership.model_validate(membership)
    session.add(db_membership)
    session.commit()
    session.refresh(db_membership)

    return db_membership


@router.patch("/{membership_id}", response_model=MembershipResponse)
def update_membership_role(membership_id: int, payload: MembershipUpdate, session: Session = Depends(sync_session)):
    db_membership = session.get(Membership, membership_id)
    if not db_membership:
        raise HTTPException(status_code=404, detail="Membership record not found")
    
    allowed_roles = {"admin","user", "member"}
    if payload.role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role '{payload.role}': Valid roles are:admin, user or member")

    data = payload.model_dump(exclude_unset=True)
    db_membership.sqlmodel_update(data)
    session.add(db_membership)
    session.commit()
    session.refresh(db_membership)
    return db_membership


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_from_organization(membership_id: int, session: Session = Depends(sync_session)):
    db_membership = session.get(Membership, membership_id)
    if not db_membership:
        raise HTTPException(status_code=404, detail="Membership record not found")
    
    session.delete(db_membership)
    session.commit()
    return None
