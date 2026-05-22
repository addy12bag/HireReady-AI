import logging

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session as get_db
from app.db import repository
from app.agents.document_parser import parse_document
from app.agents.resume_normalizer import normalize_resume
from app.agents.jd_analyzer import analyze_job_description
from app.agents.ats_scorer import score_resume
from app.agents.resume_generator import generate_resume
from app.agents.conversational import chat
from app.storage.local import get_storage
from app.schemas.resume import ResumeSchema
from app.schemas.ats_report import ATSScoreReport
from app.config import get_settings, get_llm_provider

logger = logging.getLogger(__name__)
router = APIRouter(tags=["web"])


def _templates(request: Request):
    return request.app.state.templates


# ─── Landing Page ────────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return _templates(request).TemplateResponse(request, "index.html")


@router.post("/session/create", response_class=HTMLResponse)
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    session = await repository.create_session(db, "FULL_PIPELINE")
    url = f"/session/{session.id}"
    return HTMLResponse(
        status_code=200,
        headers={"HX-Redirect": url},
        content="",
    )


# ─── Session Dashboard (Upload + JD) ────────────────────────────


@router.get("/session/{session_id}", response_class=HTMLResponse)
async def session_page(request: Request, session_id: str, db: AsyncSession = Depends(get_db)):
    session = await repository.get_session(db, session_id)
    if not session:
        return RedirectResponse("/", status_code=303)

    resume = await repository.get_resume_schema(db, session_id)
    ats = await repository.get_ats_report(db, session_id)
    generated = await repository.get_generated_resumes(db, session_id)

    return _templates(request).TemplateResponse(
        request, "session.html",
        {
            "session": session,
            "has_resume": resume is not None,
            "has_ats": ats is not None,
            "ats_report": ats.report_json if ats else None,
            "generated_resumes": generated,
        },
    )


# ─── Upload Resume (HTMX partial) ──────────────────────────────


@router.post("/session/{session_id}/upload", response_class=HTMLResponse)
async def upload_resume(
    request: Request,
    session_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    templates = _templates(request)

    session = await repository.get_session(db, session_id)
    if not session:
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": "Session not found."},
            status_code=404,
        )

    allowed = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }
    mime = file.content_type or "application/octet-stream"
    if mime not in allowed:
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": f"Unsupported file type: {mime}. Upload PDF or DOCX."},
            status_code=400,
        )

    try:
        content = await file.read()
        file_key = f"{session_id}/{file.filename}"
        storage = get_storage()
        file_path = await storage.save(file_key, content)

        await repository.create_document(
            db, session_id, file.filename or "unknown", mime, file_path, len(content)
        )

        extraction = parse_document(file_path, mime)
        if extraction.status == "FAILED":
            return templates.TemplateResponse(
                request, "partials/error_toast.html",
                {"message": "Could not extract text from this file. Try a different file."},
                status_code=422,
            )

        llm = get_llm_provider()
        schema = await normalize_resume(extraction.raw_blocks, llm)
        await repository.save_resume_schema(db, session_id, schema.model_dump(), schema.extraction_confidence)
        await repository.update_session_status(db, session_id, "PARSED")

        return templates.TemplateResponse(
            request, "partials/upload_success.html",
            {
                "filename": file.filename,
                "blocks": len(extraction.raw_blocks),
                "confidence": round(schema.extraction_confidence * 100),
                "session_id": session_id,
            },
        )

    except Exception as e:
        logger.exception("Upload failed")
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": f"Upload failed: {str(e)}"},
            status_code=500,
        )


# ─── Score Resume (HTMX redirect to results) ───────────────────


@router.post("/session/{session_id}/score", response_class=HTMLResponse)
async def score_session(
    request: Request,
    session_id: str,
    job_description: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    templates = _templates(request)

    session = await repository.get_session(db, session_id)
    if not session:
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": "Session not found."},
            status_code=404,
        )

    resume_model = await repository.get_resume_schema(db, session_id)
    if not resume_model:
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": "Upload a resume first."},
            status_code=400,
        )

    if not job_description.strip():
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": "Paste a job description to score against."},
            status_code=400,
        )

    try:
        resume_schema = ResumeSchema.model_validate(resume_model.schema_json)
        llm = get_llm_provider()

        jd_analysis = await analyze_job_description(job_description, llm)
        await repository.save_jd_analysis(db, session_id, job_description, jd_analysis.model_dump())

        ats_report = await score_resume(resume_schema, jd_analysis, llm)
        await repository.save_ats_report(
            db, session_id, ats_report.overall_score, ats_report.grade, ats_report.model_dump()
        )
        await repository.update_session_status(db, session_id, "SCORED")

        url = f"/session/{session_id}/results"
        return HTMLResponse(status_code=200, headers={"HX-Redirect": url}, content="")

    except Exception as e:
        logger.exception("Scoring failed")
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": f"Scoring failed: {str(e)}"},
            status_code=500,
        )


# ─── Results Page ───────────────────────────────────────────────


@router.get("/session/{session_id}/results", response_class=HTMLResponse)
async def results_page(request: Request, session_id: str, db: AsyncSession = Depends(get_db)):
    session = await repository.get_session(db, session_id)
    if not session:
        return RedirectResponse("/", status_code=303)

    ats = await repository.get_ats_report(db, session_id)
    if not ats:
        return RedirectResponse(f"/session/{session_id}", status_code=303)

    jd = await repository.get_jd_analysis(db, session_id)
    generated = await repository.get_generated_resumes(db, session_id)

    return _templates(request).TemplateResponse(
        request, "results.html",
        {
            "session_id": session_id,
            "ats_report": ats.report_json,
            "jd_analysis": jd.analysis_json if jd else None,
            "generated_resumes": generated,
        },
    )


# ─── Generate Resume (HTMX partial) ────────────────────────────


@router.post("/session/{session_id}/generate", response_class=HTMLResponse)
async def generate_session(
    request: Request,
    session_id: str,
    variant: str = Form("CONSERVATIVE"),
    db: AsyncSession = Depends(get_db),
):
    templates = _templates(request)

    session = await repository.get_session(db, session_id)
    if not session:
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": "Session not found."},
            status_code=404,
        )

    resume_model = await repository.get_resume_schema(db, session_id)
    ats_model = await repository.get_ats_report(db, session_id)
    if not resume_model or not ats_model:
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": "Score your resume first."},
            status_code=400,
        )

    valid = {"CONSERVATIVE", "AGGRESSIVE", "CREATIVE"}
    if variant not in valid:
        variant = "CONSERVATIVE"

    try:
        resume_schema = ResumeSchema.model_validate(resume_model.schema_json)
        ats_report = ATSScoreReport.model_validate(ats_model.report_json)
        llm = get_llm_provider()
        settings = get_settings()

        tailored, file_path, pdf_path = await generate_resume(
            resume_schema, ats_report, variant, llm, settings.storage_path
        )

        gen = await repository.save_generated_resume(
            db, session_id, variant, tailored.model_dump(), file_path, pdf_path
        )
        await repository.update_session_status(db, session_id, "GENERATED")

        return templates.TemplateResponse(
            request, "partials/generate_success.html",
            {
                "session_id": session_id,
                "resume_id": str(gen.id),
                "variant": variant,
            },
        )

    except Exception as e:
        logger.exception("Generation failed")
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": f"Generation failed: {str(e)}"},
            status_code=500,
        )


# ─── Download Resume ────────────────────────────────────────────


@router.get("/session/{session_id}/download/{resume_id}")
async def download_resume(session_id: str, resume_id: str, db: AsyncSession = Depends(get_db)):
    gen = await repository.get_generated_resume(db, resume_id)
    if not gen or gen.session_id != session_id:
        raise HTTPException(status_code=404, detail="Resume not found")

    filename = f"resume_{gen.variant.lower()}.docx"
    return FileResponse(gen.file_path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.get("/session/{session_id}/download/{resume_id}/pdf")
async def download_resume_pdf(session_id: str, resume_id: str, db: AsyncSession = Depends(get_db)):
    gen = await repository.get_generated_resume(db, resume_id)
    if not gen or gen.session_id != session_id or not gen.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found")

    filename = f"resume_{gen.variant.lower()}.pdf"
    return FileResponse(gen.pdf_path, filename=filename, media_type="application/pdf")


# ─── Chat ───────────────────────────────────────────────────────


@router.get("/session/{session_id}/chat", response_class=HTMLResponse)
async def chat_page(request: Request, session_id: str, db: AsyncSession = Depends(get_db)):
    session = await repository.get_session(db, session_id)
    if not session:
        return RedirectResponse("/", status_code=303)

    history = await repository.get_chat_history(db, session_id)

    return _templates(request).TemplateResponse(
        request, "chat.html",
        {
            "session_id": session_id,
            "messages": [{"role": m.role, "content": m.content} for m in history],
        },
    )


@router.post("/session/{session_id}/chat", response_class=HTMLResponse)
async def send_chat_message(
    request: Request,
    session_id: str,
    message: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    templates = _templates(request)

    session = await repository.get_session(db, session_id)
    if not session:
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": "Session not found."},
            status_code=404,
        )

    if not message.strip():
        return HTMLResponse(content="")

    try:
        resume_model = await repository.get_resume_schema(db, session_id)
        ats_model = await repository.get_ats_report(db, session_id)
        jd_model = await repository.get_jd_analysis(db, session_id)
        history = await repository.get_chat_history(db, session_id)

        resume_data = resume_model.schema_json if resume_model else None
        ats_data = ats_model.report_json if ats_model else None
        jd_data = jd_model.analysis_json if jd_model else None
        history_data = [{"role": m.role, "content": m.content} for m in history]

        await repository.save_chat_message(db, session_id, "user", message)

        llm = get_llm_provider()
        response_text = await chat(message, resume_data, ats_data, jd_data, history_data, llm)

        await repository.save_chat_message(db, session_id, "assistant", response_text)

        return templates.TemplateResponse(
            request, "partials/chat_message.html",
            {"role": "assistant", "content": response_text},
        )

    except Exception as e:
        logger.exception("Chat failed")
        return templates.TemplateResponse(
            request, "partials/error_toast.html",
            {"message": f"Chat failed: {str(e)}"},
            status_code=500,
        )
