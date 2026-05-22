import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session as get_db
from app.db import repository
from app.agents.document_parser import parse_document
from app.agents.resume_normalizer import normalize_resume
from app.storage.local import get_storage
from app.config import get_llm_provider
from app.api.schemas.document import DocumentUploadResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Validate session
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id: must be a valid UUID")
    session = await repository.get_session(db, str(session_uuid))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate file type
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }
    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {mime_type}")

    # Save file
    content = await file.read()
    file_key = f"{session_id}/{file.filename}"
    storage = get_storage()
    file_path = await storage.save(file_key, content)

    # Save document record
    doc = await repository.create_document(
        db, session.id, file.filename or "unknown", mime_type, file_path, len(content)
    )

    # Parse document
    extraction = parse_document(file_path, mime_type)
    if extraction.status == "FAILED":
        raise HTTPException(status_code=422, detail="Failed to extract text from document")

    # Normalize resume
    llm = get_llm_provider()
    resume_schema = await normalize_resume(extraction.raw_blocks, llm)

    # Save resume schema
    await repository.save_resume_schema(
        db, session.id, resume_schema.model_dump(), resume_schema.extraction_confidence
    )
    await repository.update_session_status(db, session.id, "PARSED")

    return DocumentUploadResponse(
        document_id=str(doc.id),
        session_id=session_id,
        filename=file.filename or "unknown",
        mime_type=mime_type,
        blocks_extracted=len(extraction.raw_blocks),
        status="SUCCESS",
    )
