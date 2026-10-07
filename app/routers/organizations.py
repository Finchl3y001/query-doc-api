from fastapi import FastAPI, Depends, status, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, Session
from fastapi.exceptions import RequestValidationError
from datetime import datetime, timezone

from ..models import OrganizationCreate, OrganizationResponse, Organization
from ..database import sync_session, async_session

router =APIRouter(tags=["Organizations"])


@router.post("/organizations")
def create_organization(org: OrganizationCreate, session: Session=Depends(sync_session)):
    statement = select(Organization).where(Organization.name == org.name)
    existing_org = session.exec(statement).all()

    if existing_org:
        field = "name" 
        value = org.name

        raise RequestValidationError([
            {
                "loc" : ("body", field),
                "msg" : f"The {field} '{value}' is already taken",
                "type": "value_error.already_exists"
            }
        ])

    db_org = Organization.model_validate(org)
    session.add(db_org)
    session.commit()
    session.refresh(db_org)

    return db_org

@router.get("/organizations", response_model = list[OrganizationResponse])
async def get_organizations(session: AsyncSession = Depends(async_session)):
    statement = select(Organization)
    results = await session.execute(statement)
    org_results = results.scalars().all()

    return org_results
