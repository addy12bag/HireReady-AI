import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session as get_db
from app.db import repository
from app.agents.conversational import chat
from app.config import get_llm_provider
from app.api.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    try:
        session_id = uuid.UUID(req.session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id: must be a valid UUID")

    # Validate session
    session = await repository.get_session(db, str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get session data
    resume_model = await repository.get_resume_schema(db, str(session_id))
    ats_model = await repository.get_ats_report(db, str(session_id))
    jd_model = await repository.get_jd_analysis(db, str(session_id))
    history = await repository.get_chat_history(db, str(session_id))

    resume_data = resume_model.schema_json if resume_model else None
    ats_data = ats_model.report_json if ats_model else None
    jd_data = jd_model.analysis_json if jd_model else None
    history_data = [{"role": m.role, "content": m.content} for m in history]

    # Save user message
    await repository.save_chat_message(db, str(session_id), "user", req.message)

    # Generate response
    llm = get_llm_provider()
    response_text = await chat(
        req.message, resume_data, ats_data, jd_data, history_data, llm
    )

    # Save assistant response
    await repository.save_chat_message(db, str(session_id), "assistant", response_text)

    return ChatResponse(response=response_text, session_id=req.session_id)
