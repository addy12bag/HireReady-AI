import logging
from nltk.stem import PorterStemmer
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

stemmer = PorterStemmer()


def keyword_match_score(resume_tokens: list[str], jd_keywords: list[str]) -> tuple[float, list[str], list[str]]:
    """Compute keyword match score using stemming and fuzzy matching.
    Returns (score, matched_keywords, missing_keywords)."""
    if not jd_keywords:
        return 1.0, [], []

    matched = []
    missing = []

    for kw in jd_keywords:
        kw_stem = stemmer.stem(kw.lower())
        found = False
        for token in resume_tokens:
            token_stem = stemmer.stem(token.lower())
            if fuzz.ratio(token_stem, kw_stem) > 85:
                matched.append(kw)
                found = True
                break
        if not found:
            missing.append(kw)

    score = len(matched) / len(jd_keywords) if jd_keywords else 1.0
    return score, matched, missing


def compute_cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import numpy as np

    a_np = np.array(a)
    b_np = np.array(b)
    dot = np.dot(a_np, b_np)
    norm = np.linalg.norm(a_np) * np.linalg.norm(b_np)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def extract_resume_tokens(resume_schema: dict) -> list[str]:
    """Extract all text tokens from a resume schema for keyword matching."""
    tokens = []

    # Skills
    skills = resume_schema.get("skills", {})
    tokens.extend(skills.get("technical", []))
    tokens.extend(skills.get("soft", []))
    tokens.extend(skills.get("certifications", []))

    # Experience bullets
    for exp in resume_schema.get("experience", []):
        tokens.append(exp.get("company", ""))
        tokens.append(exp.get("title", ""))
        for bullet in exp.get("bullets", []):
            tokens.extend(bullet.get("text", "").split())

    # Summary
    if resume_schema.get("summary"):
        tokens.extend(resume_schema["summary"].split())

    # Projects
    for proj in resume_schema.get("projects", []):
        tokens.extend(proj.get("technologies", []))
        if proj.get("description"):
            tokens.extend(proj["description"].split())

    return [t for t in tokens if t]


def score_formatting(resume_schema: dict) -> float:
    """Score formatting compliance (0-100)."""
    score = 100.0

    contact = resume_schema.get("contact", {})
    if not contact.get("name"):
        score -= 20
    if not contact.get("email"):
        score -= 15
    if not contact.get("phone"):
        score -= 5

    # Standard section presence
    if not resume_schema.get("experience"):
        score -= 20
    if not resume_schema.get("education"):
        score -= 10
    if not resume_schema.get("skills", {}).get("technical"):
        score -= 10

    return max(0.0, score)


def score_completeness(resume_schema: dict) -> float:
    """Score section completeness (0-100)."""
    score = 0.0

    if resume_schema.get("summary"):
        score += 20

    experience = resume_schema.get("experience", [])
    if experience:
        score += 30
        # Check for quantified bullets
        has_metrics = any(
            b.get("has_metric") for exp in experience for b in exp.get("bullets", [])
        )
        if has_metrics:
            score += 15

    if resume_schema.get("education"):
        score += 15

    skills = resume_schema.get("skills", {})
    if skills.get("technical"):
        score += 15

    if resume_schema.get("contact", {}).get("email"):
        score += 5

    return min(100.0, score)
