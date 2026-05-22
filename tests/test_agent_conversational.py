"""Tests for app/agents/conversational.py — async, mock LLM."""
from app.agents.conversational import chat, _build_context


class TestBuildContext:
    def test_with_all_data(self, sample_resume_schema, sample_ats_report, sample_jd_analysis):
        ctx = _build_context(
            sample_resume_schema.model_dump(),
            sample_ats_report.model_dump(),
            sample_jd_analysis.model_dump(),
        )
        assert "Jane Doe" in ctx
        assert "Python" in ctx
        assert "ATS SCORE" in ctx
        assert "TARGET ROLE" in ctx

    def test_with_none_data(self):
        ctx = _build_context(None, None, None)
        assert isinstance(ctx, str)

    def test_with_partial_data(self, sample_resume_schema):
        ctx = _build_context(sample_resume_schema.model_dump(), None, None)
        assert "Jane Doe" in ctx
        assert "ATS SCORE" not in ctx


class TestChat:
    async def test_happy_path(self, mock_llm, sample_resume_schema, sample_ats_report, sample_jd_analysis):
        response = await chat(
            "What keywords am I missing?",
            sample_resume_schema.model_dump(),
            sample_ats_report.model_dump(),
            sample_jd_analysis.model_dump(),
            [],
            mock_llm,
        )
        assert isinstance(response, str)
        assert len(response) > 0

    async def test_no_context(self, mock_llm):
        response = await chat("Hello", None, None, None, [], mock_llm)
        assert isinstance(response, str)

    async def test_with_history(self, mock_llm):
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        response = await chat("What's my score?", None, None, None, history, mock_llm)
        assert isinstance(response, str)
