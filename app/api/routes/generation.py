import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session as get_db
from app.db import repository
from app.agents.resume_generator import generate_resume
from app.config import get_llm_provider
from app.schemas.resume import ResumeSchema
from app.schemas.ats_report import ATSScoreReport
from app.storage.local import get_storage
from app.config import get_settings
from app.api.schemas.generation import GenerationRequest, GenerationResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generation", tags=["generation"])


@router.post("/generate", response_model=GenerationResponse)
async def generate(req: GenerationRequest, db: AsyncSession = Depends(get_db)):
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
        raise HTTPException(status_code=400, detail="No resume uploaded")

    # Get ATS report
    ats_model = await repository.get_ats_report(db, str(session_id))
    if not ats_model:
        raise HTTPException(status_code=400, detail="No ATS score available. Run scoring first.")

    resume_schema = ResumeSchema.model_validate(resume_model.schema_json)
    ats_report = ATSScoreReport.model_validate(ats_model.report_json)

    # Validate variant
    valid_variants = {"CONSERVATIVE", "AGGRESSIVE", "CREATIVE"}
    if req.variant not in valid_variants:
        raise HTTPException(status_code=400, detail=f"Invalid variant. Must be one of: {valid_variants}")

    # Generate
    llm = get_llm_provider()
    get_storage()
    settings = get_settings()

    tailored_schema, file_path, pdf_path = await generate_resume(
        resume_schema, ats_report, req.variant, llm, settings.storage_path
    )

    # Save to DB
    gen_record = await repository.save_generated_resume(
        db, str(session_id), req.variant, tailored_schema.model_dump(), file_path, pdf_path
    )
    await repository.update_session_status(db, str(session_id), "GENERATED")

    return GenerationResponse(
        generated_resume_id=str(gen_record.id),
        session_id=req.session_id,
        variant=req.variant,
        download_url=f"/sessions/{req.session_id}/download/{gen_record.id}",
    )
