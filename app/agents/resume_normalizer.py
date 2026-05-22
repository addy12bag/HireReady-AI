import logging

from app.llm.provider import LLMProvider
from app.schemas.blocks import RawBlock
from app.schemas.resume import ResumeSchema, Contact, Experience, Education, Skills, Project, Bullet
from app.utils.nlp import (
    extract_entities,
    extract_emails,
    extract_phones,
    extract_links,
    parse_date,
    normalize_skill,
)

logger = logging.getLogger(__name__)

NORMALIZE_SYSTEM_PROMPT = """You are a resume parsing expert. Extract structured data from the resume text provided.
Return valid JSON with these fields:
{
  "contact": {"name": string, "email": string, "phone": string, "linkedin": string, "github": string, "location": {"city": string, "state": string, "country": string}},
  "summary": string | null,
  "experience": [{"company": string, "title": string, "start_date": string, "end_date": string, "location": string, "bullets": [{"text": string, "has_metric": boolean}]}],
  "education": [{"institution": string, "degree": string, "field": string, "start_date": string, "end_date": string, "gpa": string}],
  "skills": {"technical": [string], "soft": [string], "certifications": [string], "languages": [string]},
  "projects": [{"name": string, "description": string, "technologies": [string]}]
}
Rules:
- Extract ALL experience entries, even if incomplete
- Mark has_metric=true if the bullet contains numbers/percentages
- Normalize dates to "YYYY-MM" format, use "PRESENT" for current
- For skills, extract each individual skill as a separate string
- Return ONLY valid JSON, no markdown or explanation"""


def _concatenate_blocks(blocks: list[RawBlock]) -> str:
    """Concatenate raw blocks into a single text string."""
    text_blocks = [b.content for b in blocks if b.type in ("TEXT", "TABLE")]
    return "\n".join(text_blocks)


def _merge_with_llm_data(llm_data: dict, text: str) -> ResumeSchema:
    """Merge LLM extraction with NLP-based extraction for validation."""
    # Use NLP to extract/validate contact info
    emails = extract_emails(text)
    phones = extract_phones(text)
    links = extract_links(text)
    entities = extract_entities(text)

    # Build contact from LLM data, fallback to NLP
    contact_data = llm_data.get("contact", {})
    contact = Contact(
        name=contact_data.get("name") or (entities["persons"][0] if entities["persons"] else None),
        email=contact_data.get("email") or (emails[0] if emails else None),
        phone=contact_data.get("phone") or (phones[0] if phones else None),
        linkedin=contact_data.get("linkedin") or links["linkedin"],
        github=contact_data.get("github") or links["github"],
    )

    # Parse experience
    experience = []
    for i, exp in enumerate(llm_data.get("experience", [])):
        bullets = []
        for b in exp.get("bullets", []):
            bullets.append(
                Bullet(
                    text=b.get("text", ""),
                    has_metric=b.get("has_metric", False),
                )
            )
        experience.append(
            Experience(
                id=f"exp_{i}",
                company=exp.get("company"),
                title=exp.get("title"),
                start_date=parse_date(exp.get("start_date")),
                end_date=parse_date(exp.get("end_date")),
                location=exp.get("location"),
                bullets=bullets,
            )
        )

    # Parse education
    education = []
    for i, edu in enumerate(llm_data.get("education", [])):
        education.append(
            Education(
                id=f"edu_{i}",
                institution=edu.get("institution"),
                degree=edu.get("degree"),
                field=edu.get("field"),
                start_date=parse_date(edu.get("start_date")),
                end_date=parse_date(edu.get("end_date")),
                gpa=edu.get("gpa"),
            )
        )

    # Parse skills with normalization
    skills_data = llm_data.get("skills", {})
    skills = Skills(
        technical=[normalize_skill(s) for s in skills_data.get("technical", [])],
        soft=skills_data.get("soft", []),
        certifications=skills_data.get("certifications", []),
        languages=skills_data.get("languages", []),
    )

    # Parse projects
    projects = []
    for i, proj in enumerate(llm_data.get("projects", [])):
        projects.append(
            Project(
                id=f"proj_{i}",
                name=proj.get("name"),
                description=proj.get("description"),
                technologies=proj.get("technologies", []),
            )
        )

    return ResumeSchema(
        contact=contact,
        summary=llm_data.get("summary"),
        experience=experience,
        education=education,
        skills=skills,
        projects=projects,
    )


async def normalize_resume(blocks: list[RawBlock], llm: LLMProvider) -> ResumeSchema:
    """Convert raw extraction blocks into a structured ResumeSchema."""
    text = _concatenate_blocks(blocks)

    if not text.strip():
        return ResumeSchema(extraction_confidence=0.0, flagged_fields=["empty_document"])

    # LLM extraction
    llm_data = await llm.generate_json(
        prompt=f"Resume text:\n\n{text[:8000]}",
        system=NORMALIZE_SYSTEM_PROMPT,
    )

    # Merge LLM output with NLP validation
    schema = _merge_with_llm_data(llm_data, text)

    # Calculate confidence based on completeness
    confidence = 1.0
    flagged = []
    if not schema.contact.name:
        confidence -= 0.2
        flagged.append("name_missing")
    if not schema.contact.email:
        confidence -= 0.1
        flagged.append("email_missing")
    if not schema.experience:
        confidence -= 0.3
        flagged.append("no_experience")
    if not schema.skills.technical:
        confidence -= 0.1
        flagged.append("no_technical_skills")

    schema.extraction_confidence = max(0.0, confidence)
    schema.flagged_fields = flagged

    return schema
