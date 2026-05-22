"""Tests for app/agents/resume_generator.py — async, mock LLM, tmp_path."""
import os
from app.agents.resume_generator import generate_resume, rewrite_bullet, generate_summary


class TestRewriteBullet:
    async def test_happy_path(self, mock_llm):
        result = await rewrite_bullet("Built APIs", "Python", mock_llm)
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_empty_keyword(self, mock_llm):
        result = await rewrite_bullet("Built APIs", "", mock_llm)
        assert result == "Built APIs"

    async def test_empty_bullet(self, mock_llm):
        result = await rewrite_bullet("", "Python", mock_llm)
        assert result == ""

    async def test_llm_failure_returns_original(self):
        class FailLLM:
            async def generate(self, *a, **kw): raise RuntimeError("fail")
            async def generate_json(self, *a, **kw): return {}
            async def embed(self, *a, **kw): return []
        result = await rewrite_bullet("Built APIs", "Python", FailLLM())
        assert result == "Built APIs"


class TestGenerateSummary:
    async def test_happy_path(self, mock_llm, sample_resume_schema):
        result = await generate_summary(sample_resume_schema, "Software Engineer", ["Python"], mock_llm)
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_no_experience(self, mock_llm):
        from app.schemas.resume import ResumeSchema, Skills
        resume = ResumeSchema(skills=Skills(technical=["Python"]))
        result = await generate_summary(resume, "Engineer", ["Python"], mock_llm)
        assert isinstance(result, str)


class TestGenerateResume:
    async def test_conservative_variant(self, mock_llm, sample_resume_schema, sample_ats_report, tmp_path):
        tailored, docx_path, pdf_path = await generate_resume(
            sample_resume_schema, sample_ats_report, "CONSERVATIVE", mock_llm, str(tmp_path)
        )
        assert os.path.exists(docx_path)
        assert docx_path.endswith(".docx")
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")
        assert tailored.summary is not None

    async def test_aggressive_variant(self, mock_llm, sample_resume_schema, sample_ats_report, tmp_path):
        tailored, docx_path, pdf_path = await generate_resume(
            sample_resume_schema, sample_ats_report, "AGGRESSIVE", mock_llm, str(tmp_path)
        )
        assert os.path.exists(docx_path)
        assert os.path.exists(pdf_path)

    async def test_creative_variant(self, mock_llm, sample_resume_schema, sample_ats_report, tmp_path):
        tailored, docx_path, pdf_path = await generate_resume(
            sample_resume_schema, sample_ats_report, "CREATIVE", mock_llm, str(tmp_path)
        )
        assert os.path.exists(docx_path)
        assert os.path.exists(pdf_path)

    async def test_missing_skills_added(self, mock_llm, sample_resume_schema, tmp_path):
        from app.schemas.ats_report import ATSScoreReport, ScoreBreakdown, ScoreLayer, KeywordAnalysis
        report = ATSScoreReport(
            overall_score=50.0,
            grade="D",
            score_breakdown=ScoreBreakdown(
                keyword_exact_match=ScoreLayer(score=50, weight=0.3, weighted_score=15),
                semantic_similarity=ScoreLayer(score=50, weight=0.25, weighted_score=12.5),
                experience_alignment=ScoreLayer(score=50, weight=0.2, weighted_score=10),
                skills_coverage=ScoreLayer(score=50, weight=0.15, weighted_score=7.5),
                formatting_compliance=ScoreLayer(score=100, weight=0.05, weighted_score=5),
                section_completeness=ScoreLayer(score=80, weight=0.05, weighted_score=4),
            ),
            keyword_analysis=KeywordAnalysis(
                matched=["Python"],
                missing_critical=["Rust", "Go"],
                missing_preferred=["Docker"],
            ),
        )
        tailored, docx_path, pdf_path = await generate_resume(
            sample_resume_schema, report, "AGGRESSIVE", mock_llm, str(tmp_path)
        )
        # Missing critical skills should be added
        skills_lower = [s.lower() for s in tailored.skills.technical]
        assert "rust" in skills_lower
        assert "go" in skills_lower
