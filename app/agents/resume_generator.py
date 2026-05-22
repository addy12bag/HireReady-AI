import logging
import uuid

from app.llm.provider import LLMProvider
from app.schemas.resume import ResumeSchema
from app.schemas.ats_report import ATSScoreReport
from app.utils.docx_builder import build_docx
from app.utils.pdf_builder import build_pdf

logger = logging.getLogger(__name__)

BULLET_REWRITE_PROMPT = """Rewrite this resume bullet point following the XYZ framework.
Rules:
1. Start with a strong past-tense action verb
2. Include the metric if present; do NOT invent metrics
3. Naturally include the keyword if it fits contextually
4. Keep under 120 characters
5. Do not change the fundamental claim

Original: "{bullet}"
Target keyword: "{keyword}"

Return ONLY the rewritten bullet, no explanation."""

SUMMARY_PROMPT = """Write a 3-sentence professional summary for this person targeting the role of {job_title}.
Use these actual details from their resume:
- Current/most recent role: {current_role}
- Key skills: {skills}
- Notable achievements: {achievements}

Include these keywords naturally: {keywords}

Rules:
- Ground everything in actual resume data
- Do not invent experience or metrics
- Keep it under 50 words

Return ONLY the summary text, no explanation."""


async def rewrite_bullet(bullet_text: str, keyword: str, llm: LLMProvider) -> str:
    """Rewrite a single bullet point with keyword optimization."""
    if not keyword or not bullet_text.strip():
        return bullet_text

    try:
        result = await llm.generate(
            prompt=BULLET_REWRITE_PROMPT.format(bullet=bullet_text, keyword=keyword),
            temperature=0.5,
        )
        return result.strip().strip('"')
    except Exception as e:
        logger.warning(f"Bullet rewrite failed: {e}")
        return bullet_text


async def generate_summary(
    resume: ResumeSchema, job_title: str, keywords: list[str], llm: LLMProvider
) -> str:
    """Generate a tailored professional summary."""
    current_role = resume.experience[0].title if resume.experience else "professional"
    skills = ", ".join(resume.skills.technical[:10])
    achievements = " ".join(
        b.text for exp in resume.experience[:2] for b in exp.bullets[:2]
    )

    try:
        return await llm.generate(
            prompt=SUMMARY_PROMPT.format(
                job_title=job_title,
                current_role=current_role,
                skills=skills,
                achievements=achievements[:300],
                keywords=", ".join(keywords[:5]),
            ),
            temperature=0.5,
        )
    except Exception as e:
        logger.warning(f"Summary generation failed: {e}")
        return resume.summary or ""


async def generate_resume(
    resume_schema: ResumeSchema,
    ats_report: ATSScoreReport,
    variant: str,
    llm: LLMProvider,
    storage_path: str,
) -> tuple[ResumeSchema, str, str]:
    """Generate a tailored resume variant and save as both DOCX and PDF.

    Returns (tailored_schema, docx_path, pdf_path).
    """
    # Create a copy of the schema to modify
    tailored = resume_schema.model_copy(deep=True)

    # Get top missing keywords for injection
    missing = ats_report.keyword_analysis.missing_critical[:3]
    if variant == "AGGRESSIVE":
        missing += ats_report.keyword_analysis.missing_preferred[:3]

    # Generate tailored summary
    job_title = "the target role"
    tailored.summary = await generate_summary(resume_schema, job_title, missing, llm)

    # Rewrite bullets for top experiences
    if variant != "CONSERVATIVE":
        for exp in tailored.experience[:3]:
            for i, bullet in enumerate(exp.bullets[:3]):
                keyword = missing[i % len(missing)] if missing else ""
                exp.bullets[i].text = await rewrite_bullet(bullet.text, keyword, llm)

    # Ensure all missing critical skills are in skills section
    existing_skills = set(s.lower() for s in tailored.skills.technical)
    for skill in missing:
        if skill.lower() not in existing_skills:
            tailored.skills.technical.append(skill)

    # Build both DOCX and PDF
    base_name = f"{uuid.uuid4()}_{variant}"
    docx_path = f"{storage_path}/{base_name}.docx"
    pdf_path = f"{storage_path}/{base_name}.pdf"

    build_docx(tailored, docx_path)
    build_pdf(tailored, pdf_path)

    return tailored, docx_path, pdf_path
