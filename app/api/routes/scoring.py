import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session as get_db
from app.db import repository
from app.agents.jd_analyzer import analyze_job_description
from app.agents.ats_scorer import score_resume
from app.config import get_llm_provider
from app.schemas.resume import ResumeSchema
from app.api.schemas.scoring import ScoringRequest, ScoringResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.post("/analyze", response_model=ScoringResponse)
async def analyze(req: ScoringRequest, db: AsyncSession = Depends(get_db)):
    try:
        session_id = uuid.UUID(req.session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id: must be a valid UUID")

    # Validate session
    session = await repository.get_session(db, str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get resume schema
    resume_model = await repository.get_resume_schema(db, str(session_id))
    if not resume_model:
        raise HTTPException(status_code=400, detail="No resume uploaded for this session")

    resume_schema = ResumeSchema.model_validate(resume_model.schema_json)

    # Analyze JD
    llm = get_llm_provider()
    jd_analysis = await analyze_job_description(req.job_description_text, llm)

    # Save JD analysis
    await repository.save_jd_analysis(
        db, str(session_id), req.job_description_text, jd_analysis.model_dump()
    )

    # Score
    ats_report = await score_resume(resume_schema, jd_analysis, llm)

    # Save ATS report
    await repository.save_ats_report(
        db, str(session_id), ats_report.overall_score, ats_report.grade, ats_report.model_dump()
    )
    await repository.update_session_status(db, str(session_id), "SCORED")

    return ScoringResponse(
        session_id=req.session_id,
        overall_score=ats_report.overall_score,
        grade=ats_report.grade,
        report=ats_report.model_dump(),
    )
