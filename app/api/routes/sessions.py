import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session as get_db
from app.db import repository
from app.api.schemas.session import SessionCreateRequest, SessionCreateResponse, SessionDetailResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreateResponse)
async def create_session(req: SessionCreateRequest, db: AsyncSession = Depends(get_db)):
    session = await repository.create_session(db, req.task_type, req.user_id)
    return SessionCreateResponse(
        session_id=str(session.id),
        task_type=session.task_type,
        status=session.status,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id: must be a valid UUID")
    session = await repository.get_session(db, str(session_uuid))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    resume = await repository.get_resume_schema(db, session.id)
    jd = await repository.get_jd_analysis(db, session.id)
    ats = await repository.get_ats_report(db, session.id)

    return SessionDetailResponse(
        session_id=str(session.id),
        user_id=session.user_id,
        task_type=session.task_type,
        status=session.status,
        has_resume=resume is not None,
        has_jd=jd is not None,
        has_ats_report=ats is not None,
    )


@router.get("/{session_id}/download/{resume_id}")
async def download_resume(session_id: str, resume_id: str, db: AsyncSession = Depends(get_db)):
    from app.db.models import GeneratedResumeModel
    from sqlalchemy import select

    try:
        session_uuid = uuid.UUID(session_id)
        resume_uuid = uuid.UUID(resume_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    result = await db.execute(
        select(GeneratedResumeModel).where(
            GeneratedResumeModel.id == str(resume_uuid),
            GeneratedResumeModel.session_id == str(session_uuid),
        )
    )
    record = result.scalar_one_or_none()
    if not record or not record.file_path:
        raise HTTPException(status_code=404, detail="Generated resume not found")

    file_path = Path(record.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=f"resume_{record.variant}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
