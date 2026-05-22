from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    SessionModel,
    DocumentModel,
    ResumeSchemaModel,
    JDAnalysisModel,
    ATSReportModel,
    GeneratedResumeModel,
    ChatMessageModel,
)


async def create_session(db: AsyncSession, task_type: str, user_id: str = "anonymous") -> SessionModel:
    session = SessionModel(task_type=task_type, user_id=user_id)
    db.add(session)
    await db.flush()
    return session


async def get_session(db: AsyncSession, session_id: str) -> SessionModel | None:
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    return result.scalar_one_or_none()


async def update_session_status(db: AsyncSession, session_id: str, status: str) -> None:
    session = await get_session(db, session_id)
    if session:
        session.status = status


async def create_document(
    db: AsyncSession,
    session_id: str,
    filename: str,
    mime_type: str,
    file_path: str,
    file_size: int | None = None,
) -> DocumentModel:
    doc = DocumentModel(
        session_id=session_id,
        filename=filename,
        mime_type=mime_type,
        file_path=file_path,
        file_size_bytes=file_size,
    )
    db.add(doc)
    await db.flush()
    return doc


async def save_resume_schema(
    db: AsyncSession, session_id: str, schema_json: dict, confidence: float | None = None
) -> ResumeSchemaModel:
    existing = await db.execute(
        select(ResumeSchemaModel).where(ResumeSchemaModel.session_id == session_id)
    )
    existing_record = existing.scalar_one_or_none()
    if existing_record:
        existing_record.schema_json = schema_json
        existing_record.extraction_confidence = confidence
        return existing_record

    record = ResumeSchemaModel(session_id=session_id, schema_json=schema_json, extraction_confidence=confidence)
    db.add(record)
    await db.flush()
    return record


async def get_resume_schema(db: AsyncSession, session_id: str) -> ResumeSchemaModel | None:
    result = await db.execute(
        select(ResumeSchemaModel).where(ResumeSchemaModel.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def save_jd_analysis(
    db: AsyncSession, session_id: str, raw_text: str, analysis_json: dict
) -> JDAnalysisModel:
    existing = await db.execute(
        select(JDAnalysisModel).where(JDAnalysisModel.session_id == session_id)
    )
    existing_record = existing.scalar_one_or_none()
    if existing_record:
        existing_record.raw_text = raw_text
        existing_record.analysis_json = analysis_json
        return existing_record

    record = JDAnalysisModel(session_id=session_id, raw_text=raw_text, analysis_json=analysis_json)
    db.add(record)
    await db.flush()
    return record


async def get_jd_analysis(db: AsyncSession, session_id: str) -> JDAnalysisModel | None:
    result = await db.execute(
        select(JDAnalysisModel).where(JDAnalysisModel.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def save_ats_report(
    db: AsyncSession, session_id: str, overall_score: float, grade: str, report_json: dict
) -> ATSReportModel:
    existing = await db.execute(
        select(ATSReportModel).where(ATSReportModel.session_id == session_id)
    )
    existing_record = existing.scalar_one_or_none()
    if existing_record:
        existing_record.overall_score = overall_score
        existing_record.grade = grade
        existing_record.report_json = report_json
        return existing_record

    record = ATSReportModel(
        session_id=session_id, overall_score=overall_score, grade=grade, report_json=report_json
    )
    db.add(record)
    await db.flush()
    return record


async def get_ats_report(db: AsyncSession, session_id: str) -> ATSReportModel | None:
    result = await db.execute(
        select(ATSReportModel).where(ATSReportModel.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def save_generated_resume(
    db: AsyncSession, session_id: str, variant: str, schema_json: dict,
    file_path: str | None = None, pdf_path: str | None = None,
) -> GeneratedResumeModel:
    record = GeneratedResumeModel(
        session_id=session_id, variant=variant, schema_json=schema_json,
        file_path=file_path, pdf_path=pdf_path,
    )
    db.add(record)
    await db.flush()
    return record


async def get_generated_resume(db: AsyncSession, resume_id: str) -> GeneratedResumeModel | None:
    result = await db.execute(select(GeneratedResumeModel).where(GeneratedResumeModel.id == resume_id))
    return result.scalar_one_or_none()


async def get_generated_resumes(db: AsyncSession, session_id: str) -> list[GeneratedResumeModel]:
    result = await db.execute(
        select(GeneratedResumeModel).where(GeneratedResumeModel.session_id == session_id)
    )
    return list(result.scalars().all())


async def save_chat_message(
    db: AsyncSession, session_id: str, role: str, content: str
) -> ChatMessageModel:
    record = ChatMessageModel(session_id=session_id, role=role, content=content)
    db.add(record)
    await db.flush()
    return record


async def get_chat_history(db: AsyncSession, session_id: str, limit: int = 10) -> list[ChatMessageModel]:
    result = await db.execute(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == session_id)
        .order_by(ChatMessageModel.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))
