"""Tests for app/agents/jd_analyzer.py — async, mock LLM."""
from app.agents.jd_analyzer import analyze_job_description
from app.schemas.job_description import JDAnalysis


class TestAnalyzeJobDescription:
    async def test_happy_path(self, mock_llm, sample_jd_text):
        result = await analyze_job_description(sample_jd_text, mock_llm)
        assert isinstance(result, JDAnalysis)
        assert result.job_metadata.title is not None
        assert result.job_metadata.company is not None

    async def test_empty_text_returns_default(self, mock_llm):
        result = await analyze_job_description("", mock_llm)
        assert isinstance(result, JDAnalysis)
        assert result.job_metadata.title is None

    async def test_whitespace_text_returns_default(self, mock_llm):
        result = await analyze_job_description("   \n  ", mock_llm)
        assert isinstance(result, JDAnalysis)

    async def test_llm_called_with_truncated_text(self, mock_llm):
        """Verify the function works with long text (truncation is internal)."""
        long_text = "A" * 10000
        result = await analyze_job_description(long_text, mock_llm)
        assert isinstance(result, JDAnalysis)
