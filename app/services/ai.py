# app/services/ai.py
import os
import time
from pypdf import PdfReader
from mistralai.client import Mistral  # <-- Use Mistral instead of OpenAI
from sqlmodel import Session
from app.models import DocumentChunk
from app.core.config import get_settings
from contextlib import contextmanager

settings = get_settings()
# 1. Initialize the free Mistral client
mistral_client = Mistral(api_key=settings.MISTRAL_API_KEY)


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    return chunks


# app/services/ai.py
import os
import time
from pypdf import PdfReader
from mistralai.client import Mistral  # Updated for Mistral SDK v2+

from app.models import DocumentChunk
from app.core.config import get_settings

# Initialize client using your secure, non-hardcoded configuration
settings = get_settings()
mistral_client = Mistral(api_key=settings.MISTRAL_API_KEY)


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """Splits raw text strings into overlapping structural snippets."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    return chunks


def process_document_pipeline(document_id: str, storage_path: str, organization_id: int):
    """
    Asynchronous Background Task Pipeline.
    Extracts text -> Chunks text -> Generates Vectors via Mistral -> Saves to PostgreSQL.
    
    Includes a 1.1s throttling delay to safely respect Mistral's Free Tier limits 
    (1 request/sec) without freezing the main application thread.
    """

        # 🚨 LOUD LOG 1: Check if the background worker even wakes up
    print(f"\n=======================================================")
    print(f"[BACKGROUND WORKER] Waking up for Doc ID: {document_id}")
    print(f"[BACKGROUND WORKER] Checking file path: {storage_path}")
    print(f"[BACKGROUND WORKER] File exists locally? {os.path.exists(storage_path)}")
    print(f"=======================================================\n")

    extracted_text = ""

    # 1. Parse content based on target file format
    if storage_path.endswith(".pdf"):
        try:
            reader = PdfReader(storage_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
        except Exception as e:
            print(f"[-] [Doc {document_id}] PDF extraction failure: {str(e)}")
            return
    else:
        # Plain text fallback handling (.txt, .md, etc.)
        try:
            with open(storage_path, "r", encoding="utf-8") as f:
                extracted_text = f.read()
        except Exception as e:
            print(f"[-] [Doc {document_id}] Text file reading failure: {str(e)}")
            return

    # Check for edge case where file contains only empty white spaces or imagery scanned text
    if not extracted_text.strip():
        print(f"[-] [Doc {document_id}] Aborted: No extractable text found in file matrix.")
        return

    # 2. Split file text into manageable parts
    text_snippets = chunk_text(extracted_text)
    print(f"[+] [Doc {document_id}] Document successfully partitioned into {len(text_snippets)} text chunks.")

    # 3. Pull a fresh database session link (Required outside request-response context lifecycles)
    from app.database import sync_session

    BATCH_SIZE = 32
    
    with contextmanager(sync_session)() as session:
        try:
            # Loop through your chunks in batches (steps of BATCH_SIZE)
            for i in range(0, len(text_snippets), BATCH_SIZE):
                batch_chunks = text_snippets[i : i + BATCH_SIZE]
                
                # Send the entire batch to Mistral in ONE single network call! 🚀
                response = mistral_client.embeddings.create(
                    model="mistral-embed",
                    inputs=batch_chunks
                )
                
                # Map the returned arrays back to your database models
                for j, chunk_data in enumerate(response.data):
                    vector_array = chunk_data.embedding
                    
                    db_chunk = DocumentChunk(
                        document_id=document_id,
                        organization_id=organization_id,
                        content=batch_chunks[j],
                        embedding=vector_array
                    )
                    session.add(db_chunk)
                
                print(f"[~] [Doc {document_id}] Batch processed successfully: {i + len(batch_chunks)}/{len(text_snippets)} chunks loaded.")
                
                # We add a 2-second sleep between BATCHES instead of between single chunks
                if i + BATCH_SIZE < len(text_snippets):
                    time.sleep(2.0)
            
            # Save everything to PostgreSQL at once
            session.commit()
            print(f"[+] [Doc {document_id}] SUCCESS! All vector rows committed to database.")
            
        except Exception as e:
            session.rollback()
            print(f"[-] [Doc {document_id}] Error in batch pipeline execution: {str(e)}")
        finally:
            session.close()  # Hand connection pool resources back to the Postgres daemon safely
