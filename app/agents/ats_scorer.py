import logging

from app.llm.provider import LLMProvider
from app.schemas.resume import ResumeSchema
from app.schemas.job_description import JDAnalysis
from app.schemas.ats_report import (
    ATSScoreReport,
    ScoreBreakdown,
    ScoreLayer,
    KeywordAnalysis,
    GapItem,
)
from app.utils.scoring import (
    keyword_match_score,
    compute_cosine_similarity,
    extract_resume_tokens,
    score_formatting,
    score_completeness,
)

logger = logging.getLogger(__name__)

# Scoring weights
WEIGHTS = {
    "keyword_exact_match": 0.30,
    "semantic_similarity": 0.25,
    "experience_alignment": 0.20,
    "skills_coverage": 0.15,
    "formatting_compliance": 0.05,
    "section_completeness": 0.05,
}


def _compute_grade(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    return "F"


def _keyword_layer(resume_schema: ResumeSchema, jd: JDAnalysis) -> tuple[float, dict]:
    """Layer 1: Exact keyword matching."""
    resume_tokens = extract_resume_tokens(resume_schema.model_dump())
    jd_keywords = jd.ats_keywords + [r.skill for r in jd.requirements.hard]

    # Deduplicate
    jd_keywords = list(set(kw.strip() for kw in jd_keywords if kw.strip()))

    score, matched, missing = keyword_match_score(resume_tokens, jd_keywords)

    missing_critical = [
        r.skill for r in jd.requirements.hard if r.mandatory and r.skill in missing
    ]
    missing_preferred = [
        r.skill for r in jd.requirements.hard if not r.mandatory and r.skill in missing
    ]

    return score * 100, {
        "matched": matched,
        "missing_critical": missing_critical,
        "missing_preferred": missing_preferred,
    }


async def _semantic_layer(
    resume_schema: ResumeSchema, jd: JDAnalysis, llm: LLMProvider
) -> float:
    """Layer 2: Semantic similarity using embeddings."""
    # Build resume text from key sections
    resume_parts = []
    if resume_schema.summary:
        resume_parts.append(resume_schema.summary)
    for exp in resume_schema.experience[:3]:  # Top 3 experiences
        resume_parts.append(f"{exp.title or ''} at {exp.company or ''}: " + " ".join(b.text for b in exp.bullets))
    resume_text = "\n".join(resume_parts)

    # Build JD text
    jd_parts = []
    for req in jd.requirements.hard:
        jd_parts.append(f"{req.skill} ({req.years or '?'} years)")
    jd_text = "Requirements: " + ", ".join(jd_parts)

    try:
        embeddings = await llm.embed([resume_text[:2000], jd_text[:2000]])
        return compute_cosine_similarity(embeddings[0], embeddings[1]) * 100
    except Exception as e:
        logger.warning(f"Semantic similarity failed: {e}")
        return 50.0  # Fallback


def _experience_layer(resume_schema: ResumeSchema, jd: JDAnalysis) -> float:
    """Layer 3: Experience alignment."""
    score = 50.0  # Base

    # Check seniority signals
    resume_text = " ".join(
        b.text.lower() for exp in resume_schema.experience for b in exp.bullets
    )
    seniority_hits = sum(1 for s in jd.seniority_signals if s.lower() in resume_text)
    if jd.seniority_signals:
        score += (seniority_hits / len(jd.seniority_signals)) * 30

    # Check domain knowledge
    domain_hits = sum(1 for d in jd.requirements.domain_knowledge if d.lower() in resume_text)
    if jd.requirements.domain_knowledge:
        score += (domain_hits / len(jd.requirements.domain_knowledge)) * 20

    return min(100.0, score)


def _skills_coverage_layer(resume_schema: ResumeSchema, jd: JDAnalysis) -> float:
    """Layer 4: Skills coverage."""
    resume_skills = set(s.lower() for s in resume_schema.skills.technical)
    jd_skills = set(r.skill.lower() for r in jd.requirements.hard)

    if not jd_skills:
        return 100.0

    # Weight mandatory skills higher
    mandatory_skills = {r.skill.lower() for r in jd.requirements.hard if r.mandatory}
    mandatory_hits = len(resume_skills & mandatory_skills)
    total_mandatory = len(mandatory_skills)

    all_hits = len(resume_skills & jd_skills)
    total = len(jd_skills)

    if total == 0:
        return 100.0

    # 70% weight on mandatory, 30% on all
    mandatory_score = (mandatory_hits / total_mandatory * 100) if total_mandatory > 0 else 100
    overall_score = (all_hits / total) * 100

    return mandatory_score * 0.7 + overall_score * 0.3


async def score_resume(
    resume_schema: ResumeSchema, jd: JDAnalysis, llm: LLMProvider
) -> ATSScoreReport:
    """Compute ATS compatibility score with 6-layer breakdown."""
    # Layer 1: Keyword match
    kw_score, kw_details = _keyword_layer(resume_schema, jd)

    # Layer 2: Semantic similarity
    sem_score = await _semantic_layer(resume_schema, jd, llm)

    # Layer 3: Experience alignment
    exp_score = _experience_layer(resume_schema, jd)

    # Layer 4: Skills coverage
    skills_score = _skills_coverage_layer(resume_schema, jd)

    # Layer 5: Formatting compliance
    fmt_score = score_formatting(resume_schema.model_dump())

    # Layer 6: Section completeness
    comp_score = score_completeness(resume_schema.model_dump())

    # Build breakdown
    breakdown = ScoreBreakdown(
        keyword_exact_match=ScoreLayer(score=kw_score, weight=WEIGHTS["keyword_exact_match"], weighted_score=kw_score * WEIGHTS["keyword_exact_match"]),
        semantic_similarity=ScoreLayer(score=sem_score, weight=WEIGHTS["semantic_similarity"], weighted_score=sem_score * WEIGHTS["semantic_similarity"]),
        experience_alignment=ScoreLayer(score=exp_score, weight=WEIGHTS["experience_alignment"], weighted_score=exp_score * WEIGHTS["experience_alignment"]),
        skills_coverage=ScoreLayer(score=skills_score, weight=WEIGHTS["skills_coverage"], weighted_score=skills_score * WEIGHTS["skills_coverage"]),
        formatting_compliance=ScoreLayer(score=fmt_score, weight=WEIGHTS["formatting_compliance"], weighted_score=fmt_score * WEIGHTS["formatting_compliance"]),
        section_completeness=ScoreLayer(score=comp_score, weight=WEIGHTS["section_completeness"], weighted_score=comp_score * WEIGHTS["section_completeness"]),
    )

    overall = sum(
        layer.weighted_score
        for layer in [
            breakdown.keyword_exact_match,
            breakdown.semantic_similarity,
            breakdown.experience_alignment,
            breakdown.skills_coverage,
            breakdown.formatting_compliance,
            breakdown.section_completeness,
        ]
    )

    # Generate gap analysis
    gap_analysis = []
    for skill in kw_details["missing_critical"]:
        gap_analysis.append(
            GapItem(
                gap=f"Missing required skill: {skill}",
                severity="HIGH",
                suggestion=f"Add {skill} to your skills section or incorporate it into relevant experience bullets",
                evidence_from_jd=f"{skill} listed as required",
            )
        )

    return ATSScoreReport(
        overall_score=round(overall, 1),
        grade=_compute_grade(overall),
        score_breakdown=breakdown,
        keyword_analysis=KeywordAnalysis(
            matched=kw_details["matched"],
            missing_critical=kw_details["missing_critical"],
            missing_preferred=kw_details["missing_preferred"],
        ),
        gap_analysis=gap_analysis,
        estimated_pass_rate=min(1.0, overall / 100 * 1.1),
    )
