import os
import uuid
import shutil
import numpy as np
import asyncio
import hashlib
from fastapi import APIRouter, Depends, UploadFile, HTTPException, Header, status, BackgroundTasks
from sqlmodel import select, Session
from sqlalchemy.ext.asyncio import AsyncSession
from mistralai.client import Mistral
from pydantic import BaseModel

from app.core.config import get_settings
from ..models import User, Document, UserRole, DocumentChunk
from ..dependencies import RoleChecker, validated_uploaded_file
from ..database import sync_session, async_session
from ..services.ai import process_document_pipeline

# Simple schema request structure representing incoming user prompts
class QueryRequest(BaseModel):
    question: str
    max_results: int = 3


router = APIRouter(prefix='/documents', tags=["Documents"])

settings = get_settings()
mistral_client = Mistral(api_key=settings.MISTRAL_API_KEY.get_secret_value())

UPLOAD_DIR = "storage/documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("")
async def get_documents(
    x_organization_id: int = Header(alias='X-Organization-ID'),
    user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.MEMBER, UserRole.VIEWER])),
    session: AsyncSession = Depends(async_session)
):
    statement = select(Document).where(Document.organization_id == x_organization_id)
    results = await session.execute(statement)
    documents = results.scalars().all()
    return documents


@router.post("/upload", status_code = status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks, 
    file: UploadFile = Depends(validated_uploaded_file),
    x_organization_id: int = Header(alias='X-Organization-ID'),
    session: Session = Depends(sync_session),
    user: User = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER, UserRole.MEMBER])),
):
    sha256_hash = hashlib.sha256()

    #chunked hashing protects your server's internal resource pipeline
    chunk_size = 64 * 1024

    #walrus operator - Assigns the bytes to 'chunk' AND checks if 'chunk' has data at the same time!
    while chunk := await file.read(chunk_size):
        sha256_hash.update(chunk)

    await file.seek(0)

    hex_digest = sha256_hash.hexdigest()

    existing_doc = session.query(Document).filter(
        Document.file_hash == hex_digest,
        Document.organization_id == x_organization_id
        ).first()
    
    if existing_doc:
        raise HTTPException(
            status_code = status.HTTP_409_C0NFLICT,
            detail = {
                "message" : "This exact file has already been uploaded.",
                "existing_file_id": str(existing_doc),
                "original_name" : existing_doc.filename
            }
        )
    
    file_id = uuid.uuid4()

    filename = file.filename or ""
    file_extension = os.path.splitext(file.filename)[1].lower()

    unique_filename = f"{file_id}{file_extension}"
    storage_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(storage_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to write document to disk storage"
        )
    
    db_document = Document(
        id=file_id,
        filename=file.filename,
        storage_path=storage_path,
        organization_id=x_organization_id,
        uploaded_by=user.id,
        file_hash=hex_digest
    )

    session.add(db_document)
    session.commit()
    session.refresh(db_document)
    '''
    # 5. Hand the processing over to your Mistral AI pipeline background thread! 🚀
    background_tasks.add_task(
        process_document_pipeline,
        document_id=db_document.id,
        storage_path=db_document.storage_path,
        organization_id=x_organization_id
    )'''

    process_document_pipeline(
        document_id=str(db_document.id),
        storage_path=db_document.storage_path,
        organization_id=x_organization_id
    )  
    return db_document  

    return {
        "Message": "Document uploaded successfully. Processing pipeline started in background.", 
        "document_id": db_document.id
    }


@router.delete("/{doc_id}")
def delete_document(
    doc_id: uuid.UUID,
    x_organization_id: int = Header(alias="X-Organization-ID"),
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


@router.post("/query", status_code=status.HTTP_200_OK)
async def query_knowledge_base(
    payload: QueryRequest,
    x_organization_id: int = Header(alias="X-Organization-ID"),
    current_user: User = Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER, UserRole.MEMBER, UserRole.VIEWER])),
    session: AsyncSession = Depends(async_session)
):
    """
    Exposed RAG (Retrieval-Augmented Generation) Endpoint.
    Vector searches your organization's documents, sends snippets to Mistral, and outputs answers.
    """
    settings = get_settings()
    mistral_client = Mistral(api_key=settings.MISTRAL_API_KEY.get_secret_value())

    # 1. Vectorize the incoming question string using Mistral's cloud embedding model
    try:
        embedding_response = await mistral_client.embeddings.create_async(
            model="mistral-embed",
            inputs=[payload.question]
        )
        question_vector = embedding_response.data[0].embedding
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to calculate vector metrics from Mistral: {str(e)}"
        )
    await asyncio.sleep(1.5)

    # 2. Fetch all chunk assets associated with this isolated multi-tenant corporate partition
    statement = select(DocumentChunk).where(DocumentChunk.organization_id == x_organization_id)
    db_results = await session.execute(statement)
    all_chunks = db_results.scalars().all()

    if not all_chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document intelligence matrix context data found for this workspace. Please upload files first."
        )

    # 3. Calculate Cosine Similarity math vectors locally
    # (High-value engineering technique: maps vector matrices without adding external system dependencies)
    scored_chunks = []
    q_vec = np.array(question_vector)
    
    for chunk in all_chunks:
        # Pull text matrix array back from JSON column field
        c_vec = np.array(chunk.embedding)
        # Cosine similarity formula calculation step
        similarity = np.dot(q_vec, c_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(c_vec))
        scored_chunks.append((similarity, chunk.content))

    # Sort records descending (highest match accuracy values at top) and pick the top results
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_matches = scored_chunks[:payload.max_results]
    
    # 4. Synthesize the matching results into a single context snippet block
    retrieved_context = "\n---\n".join([content for _, content in top_matches])

    # 5. Route the context data block to Mistral's fast model to formulate a clear, natural answer
    try:
        ai_chat_response = await mistral_client.chat.complete_async(
            model="mistral-small-latest",
            messages=[
                {
                    "role": "system",
                    "content": "You are a secure document assistant. Answer the question using ONLY the provided document context snippets. If the context does not contain the answer, say 'I cannot find that information in your workspace documents.'"
                },
                {
                    "role": "user",
                    "content": f"Workspace Context Data:\n{retrieved_context}\n\nUser Question: {payload.question}"
                }
            ],
            temperature=0.1 # Low variance ensures the AI states strict facts without hallucinating values
        )
        answer = ai_chat_response.choices[0].message.content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Mistral inference text generation engine failed: {str(e)}"
        )

    return {
        "answer": answer,
        "sources_analyzed": len(top_matches)
    }