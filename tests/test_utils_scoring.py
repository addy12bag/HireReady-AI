"""Tests for app/utils/scoring.py — pure functions, no mocking needed."""
from app.utils.scoring import (
    keyword_match_score,
    compute_cosine_similarity,
    extract_resume_tokens,
    score_formatting,
    score_completeness,
)


# ── keyword_match_score ───────────────────────────────────────────

class TestKeywordMatchScore:
    def test_all_match(self):
        score, matched, missing = keyword_match_score(["Python", "FastAPI"], ["Python", "FastAPI"])
        assert score == 1.0
        assert len(matched) == 2
        assert len(missing) == 0

    def test_no_match(self):
        score, matched, missing = keyword_match_score(["Java"], ["Python", "FastAPI"])
        assert score == 0.0
        assert len(matched) == 0
        assert len(missing) == 2

    def test_partial_match(self):
        score, matched, missing = keyword_match_score(["Python", "Docker"], ["Python", "FastAPI"])
        assert score == 0.5
        assert len(matched) == 1
        assert len(missing) == 1

    def test_empty_keywords(self):
        score, matched, missing = keyword_match_score(["Python"], [])
        assert score == 1.0

    def test_fuzzy_stemming(self):
        # "running" and "run" share the same stem
        score, matched, missing = keyword_match_score(["running"], ["run"])
        assert score == 1.0


# ── compute_cosine_similarity ─────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert compute_cosine_similarity([1, 2, 3], [1, 2, 3]) == 1.0

    def test_orthogonal_vectors(self):
        assert abs(compute_cosine_similarity([1, 0], [0, 1])) < 1e-10

    def test_zero_vector(self):
        assert compute_cosine_similarity([0, 0], [1, 2]) == 0.0

    def test_opposite_vectors(self):
        assert abs(compute_cosine_similarity([1, 0], [-1, 0]) - (-1.0)) < 1e-10


# ── extract_resume_tokens ─────────────────────────────────────────

class TestExtractResumeTokens:
    def test_full_schema(self):
        schema = {
            "skills": {"technical": ["Python", "FastAPI"], "soft": ["Leadership"]},
            "experience": [
                {"company": "Acme", "title": "Engineer", "bullets": [{"text": "Built APIs"}]}
            ],
            "summary": "Experienced engineer",
            "projects": [{"technologies": ["Docker"], "description": "Deployed services"}],
        }
        tokens = extract_resume_tokens(schema)
        assert "Python" in tokens
        assert "FastAPI" in tokens
        assert "Leadership" in tokens
        assert "Acme" in tokens
        assert "Engineer" in tokens
        assert "Built" in tokens
        assert "APIs" in tokens
        assert "Docker" in tokens

    def test_empty_schema(self):
        tokens = extract_resume_tokens({})
        assert tokens == []

    def test_minimal_schema(self):
        schema = {"skills": {"technical": ["Python"]}}
        tokens = extract_resume_tokens(schema)
        assert tokens == ["Python"]


# ── score_formatting ──────────────────────────────────────────────

class TestScoreFormatting:
    def test_full_resume(self):
        schema = {
            "contact": {"name": "Jane", "email": "j@e.com", "phone": "555"},
            "experience": [{"title": "Engineer"}],
            "education": [{"institution": "MIT"}],
            "skills": {"technical": ["Python"]},
        }
        assert score_formatting(schema) == 100.0

    def test_missing_name(self):
        schema = {
            "contact": {"email": "j@e.com"},
            "experience": [{}],
            "education": [{}],
            "skills": {"technical": ["Python"]},
        }
        # 100 - 20 (name) - 5 (phone) = 75
        assert score_formatting(schema) == 75.0

    def test_missing_email(self):
        schema = {
            "contact": {"name": "Jane"},
            "experience": [{}],
            "education": [{}],
            "skills": {"technical": ["Python"]},
        }
        # 100 - 15 (email) - 5 (phone) = 80
        assert score_formatting(schema) == 80.0

    def test_empty_schema(self):
        # 100 - 20 name - 15 email - 5 phone - 20 experience - 10 education - 10 skills = 20
        assert score_formatting({}) == 20.0

    def test_multiple_deductions(self):
        schema = {"contact": {}}
        # 100 - 20 name - 15 email - 5 phone - 20 experience - 10 education - 10 skills = 20
        assert score_formatting(schema) == 20.0


# ── score_completeness ────────────────────────────────────────────

class TestScoreCompleteness:
    def test_full_resume(self):
        schema = {
            "summary": "Experienced engineer",
            "experience": [{"bullets": [{"text": "Built APIs", "has_metric": True}]}],
            "education": [{"institution": "MIT"}],
            "skills": {"technical": ["Python"]},
            "contact": {"email": "j@e.com"},
        }
        # 20 summary + 30 experience + 15 metrics + 15 education + 15 skills + 5 email = 100
        assert score_completeness(schema) == 100.0

    def test_empty_schema(self):
        assert score_completeness({}) == 0.0

    def test_summary_only(self):
        assert score_completeness({"summary": "Hi"}) == 20.0

    def test_experience_without_metrics(self):
        schema = {"experience": [{"bullets": [{"text": "Did stuff"}]}]}
        # 30 experience, no metrics
        assert score_completeness(schema) == 30.0

    def test_capped_at_100(self):
        schema = {
            "summary": "S",
            "experience": [{"bullets": [{"text": "T", "has_metric": True}]}],
            "education": [{}],
            "skills": {"technical": ["P"]},
            "contact": {"email": "e"},
        }
        assert score_completeness(schema) == 100.0
