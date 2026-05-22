import logging

from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """You are a resume optimization assistant. You help users understand their
ATS score and improve their resume for specific job descriptions.

Rules:
1. Every claim must reference specific data from the provided context
2. If you don't have data to answer, say "I don't have enough information to answer this"
3. Offer actionable next steps
4. Be concise and direct
5. Never invent metrics or resume content"""


def _build_context(resume_schema: dict | None, ats_report: dict | None, jd_analysis: dict | None) -> str:
    """Build context string from session data."""
    parts = []

    if resume_schema:
        contact = resume_schema.get("contact", {})
        parts.append(f"CANDIDATE: {contact.get('name', 'Unknown')}")
        skills = resume_schema.get("skills", {}).get("technical", [])
        if skills:
            parts.append(f"SKILLS: {', '.join(skills[:15])}")
        exp = resume_schema.get("experience", [])
        if exp:
            parts.append(f"EXPERIENCE: {len(exp)} positions")
            for e in exp[:3]:
                parts.append(f"  - {e.get('title', '')} at {e.get('company', '')}")

    if ats_report:
        parts.append(f"\nATS SCORE: {ats_report.get('overall_score', 'N/A')}% (Grade: {ats_report.get('grade', 'N/A')})")
        breakdown = ats_report.get("score_breakdown", {})
        for layer, data in breakdown.items():
            if isinstance(data, dict):
                parts.append(f"  {layer}: {data.get('score', 0):.1f}%")
        kw = ats_report.get("keyword_analysis", {})
        if kw.get("matched"):
            parts.append(f"MATCHED KEYWORDS: {', '.join(kw['matched'][:10])}")
        if kw.get("missing_critical"):
            parts.append(f"MISSING CRITICAL: {', '.join(kw['missing_critical'])}")
        gaps = ats_report.get("gap_analysis", [])
        if gaps:
            parts.append("GAPS:")
            for g in gaps[:5]:
                parts.append(f"  - [{g.get('severity', '')}] {g.get('gap', '')}")

    if jd_analysis:
        meta = jd_analysis.get("job_metadata", {})
        if meta.get("title"):
            parts.append(f"\nTARGET ROLE: {meta['title']}")
        reqs = jd_analysis.get("requirements", {}).get("hard", [])
        if reqs:
            parts.append(f"REQUIRED SKILLS: {', '.join(r.get('skill', '') for r in reqs[:10])}")

    return "\n".join(parts)


async def chat(
    message: str,
    resume_schema: dict | None,
    ats_report: dict | None,
    jd_analysis: dict | None,
    chat_history: list[dict],
    llm: LLMProvider,
) -> str:
    """Generate a chat response grounded in session data."""
    context = _build_context(resume_schema, ats_report, jd_analysis)

    # Build conversation history
    history_text = ""
    if chat_history:
        history_text = "\n\nCONVERSATION HISTORY:\n"
        for msg in chat_history[-10:]:
            role = msg.get("role", "user")
            history_text += f"{role}: {msg.get('content', '')}\n"

    prompt = f"""CONTEXT:
{context}
{history_text}

User: {message}

Respond helpfully based on the data above. If the data doesn't support an answer, say so."""

    return await llm.generate(prompt, system=CHAT_SYSTEM_PROMPT, temperature=0.3)
