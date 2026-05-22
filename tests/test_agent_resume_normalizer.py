"""Tests for app/agents/resume_normalizer.py — async, mock LLM."""
from app.agents.resume_normalizer import normalize_resume, _concatenate_blocks
from app.schemas.blocks import RawBlock
from app.schemas.resume import ResumeSchema


class TestConcatenateBlocks:
    def test_text_blocks(self):
        blocks = [
            RawBlock(block_id="1", type="TEXT", content="Hello"),
            RawBlock(block_id="2", type="TEXT", content="World"),
        ]
        assert _concatenate_blocks(blocks) == "Hello\nWorld"

    def test_table_blocks_included(self):
        blocks = [
            RawBlock(block_id="1", type="TABLE", content="col1 | col2"),
        ]
        assert "col1" in _concatenate_blocks(blocks)

    def test_image_blocks_skipped(self):
        blocks = [
            RawBlock(block_id="1", type="TEXT", content="Text"),
            RawBlock(block_id="2", type="IMAGE", content="img.png"),
        ]
        result = _concatenate_blocks(blocks)
        assert "img.png" not in result

    def test_empty_blocks(self):
        assert _concatenate_blocks([]) == ""


class TestNormalizeResume:
    async def test_happy_path(self, mock_llm, sample_resume_blocks):
        result = await normalize_resume(sample_resume_blocks, mock_llm)
        assert isinstance(result, ResumeSchema)
        assert result.contact.name == "Jane Doe"
        assert result.contact.email == "jane@example.com"
        assert len(result.experience) >= 1
        assert len(result.skills.technical) >= 1

    async def test_empty_blocks(self, mock_llm):
        result = await normalize_resume([], mock_llm)
        assert result.extraction_confidence == 0.0
        assert "empty_document" in result.flagged_fields

    async def test_confidence_scoring(self, mock_llm, sample_resume_blocks):
        result = await normalize_resume(sample_resume_blocks, mock_llm)
        # Mock LLM returns name and email, so confidence should be high
        assert result.extraction_confidence >= 0.7

    async def test_skills_normalized(self, mock_llm, sample_resume_blocks):
        result = await normalize_resume(sample_resume_blocks, mock_llm)
        # Mock returns "PostgreSQL" which should stay normalized
        assert "PostgreSQL" in result.skills.technical
