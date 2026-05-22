import logging

from app.llm.provider import LLMProvider
from app.schemas.job_description import JDAnalysis

logger = logging.getLogger(__name__)

JD_SYSTEM_PROMPT = """You are a job description analysis expert. Extract structured requirements from the job description.
Return valid JSON with this exact structure:
{
  "job_metadata": {"title": string, "company": string, "seniority": "ENTRY|MID|SENIOR|LEAD|EXECUTIVE", "employment_type": "FULL_TIME|PART_TIME|CONTRACT", "location_type": "REMOTE|HYBRID|ONSITE"},
  "requirements": {
    "hard": [{"skill": string, "years": int|null, "weight": float, "mandatory": boolean}],
    "soft": [string],
    "domain_knowledge": [string]
  },
  "ats_keywords": [string],
  "seniority_signals": [string],
  "company_culture_signals": [string],
  "jd_quality_score": float
}
Rules:
- Extract ALL hard skills mentioned, even if implied
- mandatory=true if the JD says "required", "must have", "essential"
- mandatory=false if the JD says "preferred", "nice to have", "plus"
- ats_keywords: important terms that an ATS would filter on
- jd_quality_score (0-1): how well-written and specific the JD is
- Return ONLY valid JSON"""


async def analyze_job_description(raw_text: str, llm: LLMProvider) -> JDAnalysis:
    """Parse a raw job description into structured JDAnalysis."""
    if not raw_text.strip():
        return JDAnalysis()

    result = await llm.generate_json(
        prompt=f"Job description:\n\n{raw_text[:6000]}",
        system=JD_SYSTEM_PROMPT,
    )

    return JDAnalysis.model_validate(result)
