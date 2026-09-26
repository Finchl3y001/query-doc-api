from fastapi import APIRouter, Depends
from sqlmodel import select, Session
from ..models import User
from ..dependencies import RoleChecker, UserRole

router = APIRouter(prefix='/documents')

@router.get("")
def get_documents(user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.MEMBER, UserRole.VIEWER]))):
    results = session.exec(select(Document)).all()
    return results


@router.post("/upload")
def upload_document(
    file: UploadFile,
    user: User = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER, UserRole.MEMBER]))
    ):
    return {"Message": "Document uploaded successfully"}

@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    user: User = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))
    ):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail = "Document not fount")
    
    session.delete(doc)
    session.commit()

    return {"Message": "Document_deleted"}