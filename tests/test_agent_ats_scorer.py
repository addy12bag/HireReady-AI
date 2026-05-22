"""Tests for app/agents/ats_scorer.py — async, mock LLM for embed."""
from app.agents.ats_scorer import (
    score_resume,
    _compute_grade,
    _keyword_layer,
    _semantic_layer,
    _experience_layer,
    _skills_coverage_layer,
)
from app.schemas.ats_report import ATSScoreReport


class TestComputeGrade:
    def test_a_grade(self):
        assert _compute_grade(95) == "A"
        assert _compute_grade(90) == "A"

    def test_b_grade(self):
        assert _compute_grade(89) == "B"
        assert _compute_grade(80) == "B"

    def test_c_grade(self):
        assert _compute_grade(79) == "C"
        assert _compute_grade(70) == "C"

    def test_d_grade(self):
        assert _compute_grade(69) == "D"
        assert _compute_grade(60) == "D"

    def test_f_grade(self):
        assert _compute_grade(59) == "F"
        assert _compute_grade(0) == "F"


class TestKeywordLayer:
    def test_all_keywords_matched(self, sample_resume_schema, sample_jd_analysis):
        # Resume has Python, FastAPI, PostgreSQL
        # JD requires Python, FastAPI, PostgreSQL
        score, details = _keyword_layer(sample_resume_schema, sample_jd_analysis)
        assert score > 0
        assert len(details["matched"]) >= 2

    def test_no_keywords(self, sample_resume_schema):
        from app.schemas.job_description import JDAnalysis, Requirements
        jd = JDAnalysis(requirements=Requirements(hard=[], soft=[], domain_knowledge=[]), ats_keywords=[])
        score, details = _keyword_layer(sample_resume_schema, jd)
        assert score == 100.0


class TestSemanticLayer:
    async def test_returns_score(self, sample_resume_schema, sample_jd_analysis, mock_llm):
        score = await _semantic_layer(sample_resume_schema, sample_jd_analysis, mock_llm)
        assert 0 <= score <= 100

    async def test_fallback_on_error(self, sample_resume_schema, sample_jd_analysis):
        class FailLLM:
            async def embed(self, texts):
                raise RuntimeError("fail")
            async def generate(self, *a, **kw): return ""
            async def generate_json(self, *a, **kw): return {}
        score = await _semantic_layer(sample_resume_schema, sample_jd_analysis, FailLLM())
        assert score == 50.0


class TestExperienceLayer:
    def test_base_score(self, sample_resume_schema):
        from app.schemas.job_description import JDAnalysis, Requirements
        jd = JDAnalysis(requirements=Requirements(hard=[], soft=[], domain_knowledge=[]))
        score = _experience_layer(sample_resume_schema, jd)
        assert score == 50.0  # Base only

    def test_with_seniority_signals(self, sample_resume_schema):
        from app.schemas.job_description import JDAnalysis, Requirements
        jd = JDAnalysis(
            requirements=Requirements(hard=[], soft=[], domain_knowledge=[]),
            seniority_signals=["led team"],
        )
        # Resume bullet contains "Led team of 4 engineers" — case-insensitive match
        score = _experience_layer(sample_resume_schema, jd)
        assert score > 50.0


class TestSkillsCoverageLayer:
    def test_full_coverage(self, sample_resume_schema, sample_jd_analysis):
        score = _skills_coverage_layer(sample_resume_schema, sample_jd_analysis)
        assert score > 50  # Should be high since resume has the skills

    def test_no_jd_skills(self, sample_resume_schema):
        from app.schemas.job_description import JDAnalysis, Requirements
        jd = JDAnalysis(requirements=Requirements(hard=[], soft=[], domain_knowledge=[]))
        score = _skills_coverage_layer(sample_resume_schema, jd)
        assert score == 100.0


class TestScoreResume:
    async def test_happy_path(self, sample_resume_schema, sample_jd_analysis, mock_llm):
        report = await score_resume(sample_resume_schema, sample_jd_analysis, mock_llm)
        assert isinstance(report, ATSScoreReport)
        assert 0 <= report.overall_score <= 100
        assert report.grade in ("A", "B", "C", "D", "F")
        assert report.score_breakdown is not None
        assert report.keyword_analysis is not None

    async def test_gap_analysis_for_missing_skills(self, sample_resume_schema, mock_llm):
        from app.schemas.job_description import JDAnalysis, JobMetadata, Requirements, HardRequirement
        jd = JDAnalysis(
            job_metadata=JobMetadata(title="Engineer", company="X", seniority="MID"),
            requirements=Requirements(
                hard=[
                    HardRequirement(skill="Python", mandatory=True),
                    HardRequirement(skill="Rust", mandatory=True),  # Not in resume
                ],
                soft=[],
                domain_knowledge=[],
            ),
            ats_keywords=["Python", "Rust"],
        )
        report = await score_resume(sample_resume_schema, jd, mock_llm)
        # Rust should appear as a gap
        missing = report.keyword_analysis.missing_critical
        assert "Rust" in missing

    async def test_overall_is_weighted_sum(self, sample_resume_schema, sample_jd_analysis, mock_llm):
        report = await score_resume(sample_resume_schema, sample_jd_analysis, mock_llm)
        expected = sum(layer.weighted_score for layer in [
            report.score_breakdown.keyword_exact_match,
            report.score_breakdown.semantic_similarity,
            report.score_breakdown.experience_alignment,
            report.score_breakdown.skills_coverage,
            report.score_breakdown.formatting_compliance,
            report.score_breakdown.section_completeness,
        ])
        assert abs(report.overall_score - round(expected, 1)) < 0.2
