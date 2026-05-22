import re
import logging

import dateparser
import spacy
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

_nlp = None


def get_spacy() -> spacy.language.Language:
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_lg")
        except OSError:
            logger.warning("en_core_web_lg not found, falling back to en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
    return _nlp


# Canonical skill taxonomy — maps variants to canonical names
SKILL_TAXONOMY = {
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "postgre": "PostgreSQL",
    "react.js": "React",
    "reactjs": "React",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "python3": "Python",
    "python 3": "Python",
    "js": "JavaScript",
    "ts": "TypeScript",
    "k8s": "Kubernetes",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "Google Cloud Platform",
    "google cloud": "Google Cloud Platform",
    "azure": "Azure",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "rest api": "REST API",
    "restful api": "REST API",
}


def normalize_skill(skill: str) -> str:
    """Map a raw skill string to its canonical form."""
    lower = skill.strip().lower()
    if lower in SKILL_TAXONOMY:
        return SKILL_TAXONOMY[lower]

    # Fuzzy match against known skills
    best_match = None
    best_score = 0
    for variant, canonical in SKILL_TAXONOMY.items():
        score = fuzz.ratio(lower, variant)
        if score > best_score and score > 85:
            best_score = score
            best_match = canonical

    return best_match if best_match else skill.strip().title()


def parse_date(date_str: str | None) -> str | None:
    """Normalize a date string to a consistent format."""
    if not date_str or date_str.lower() in ("present", "current", "now"):
        return "PRESENT"

    parsed = dateparser.parse(date_str)
    if parsed:
        return parsed.strftime("%Y-%m")
    return date_str


def extract_entities(text: str) -> dict:
    """Extract named entities from text using spaCy."""
    nlp = get_spacy()
    doc = nlp(text)

    entities = {
        "persons": [],
        "orgs": [],
        "locations": [],
    }

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            entities["persons"].append(ent.text)
        elif ent.label_ == "ORG":
            entities["orgs"].append(ent.text)
        elif ent.label_ in ("GPE", "LOC"):
            entities["locations"].append(ent.text)

    return entities


def extract_emails(text: str) -> list[str]:
    """Extract email addresses from text."""
    return re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)


def extract_phones(text: str) -> list[str]:
    """Extract phone numbers from text."""
    patterns = [
        r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        r"\+?\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}",
    ]
    phones = []
    for pattern in patterns:
        phones.extend(re.findall(pattern, text))
    return phones


def extract_links(text: str) -> dict:
    """Extract LinkedIn and GitHub URLs from text."""
    linkedin = re.findall(r"(?:linkedin\.com/in/[\w-]+)", text, re.IGNORECASE)
    github = re.findall(r"(?:github\.com/[\w-]+)", text, re.IGNORECASE)
    return {"linkedin": linkedin[0] if linkedin else None, "github": github[0] if github else None}
