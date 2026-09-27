import os
import uuid
import shutil
from fastapi import APIRouter, Depends, UploadFile, HTTPException, Header, status
from sqlmodel import select, Session
from sqlmodel.ext.asyncio import AsyncSession

from ..models import User, Document, UserRole
from ..dependencies import RoleChecker
from ..database import sync_session, async_session

router = APIRouter(prefix='/documents')

UPLOAD_DIR = "storage/documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("")
async def get_documents(
    x_organization_id: uuid.UUID = Header(alias='X-Organization-ID'),
    user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.MEMBER, UserRole.VIEWER])),
    session: AsyncSession = Depends(async_session)
):
    statement = session.execute(select(Document)).where(Document.organization_id == x_organization_id)
    results = await session.execute(statement)
    documents = results.scalars().all()
    return documents


@router.post("/upload")
def upload_document(
    file: UploadFile,
    x_organization_id: uuid.UUID = Header(alias='X-Organization-ID'),
    session: Session = Depends(sync_session),
    user: User = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER, UserRole.MEMBER])),
    ):

    file_id = uuid.uuid4()
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{file_id}{file_extension}"
    storage_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(storage_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = "Failed to write document to disk storage"
        )
    
    db_document=Document(
        id=file_id,
        filename=file.filename,
        storage_path=storage_path,
        organization_id=x_organization_id,
        uploaded_by=user.id
    )

    session.add(db_document)
    session.commit()
    session.refresh(db_document)
    return {
        "Message": "Document uploaded successfully", 
        "document_id": db_document.id
        }

@router.delete("/{doc_id}")
def delete_document(
    doc_id: uuid.UUID,
    x_organization_id: uuid.UUID = Header(alias="X-Organization-ID"),
    user: User = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER])),
    session: Session = Depends(sync_session)
    ):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail = "Document not fount")

    if doc.organization_id != x_organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized organization boundary mismatch",
        )
    if os.path.exists(doc.storage_path):
        os.remove(doc.storage_path)

    session.delete(doc)
    session.commit()

    return {"Message": "Document_deleted"}