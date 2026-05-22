import logging

from app.schemas.pipeline import PipelineState
from app.agents.document_parser import parse_document
from app.agents.resume_normalizer import normalize_resume
from app.agents.jd_analyzer import analyze_job_description
from app.agents.ats_scorer import score_resume
from app.agents.resume_generator import generate_resume
from app.llm.gemini import GeminiProvider
from app.schemas.blocks import RawBlock
from app.schemas.resume import ResumeSchema
from app.schemas.job_description import JDAnalysis
from app.schemas.ats_report import ATSScoreReport
from app.config import get_settings

logger = logging.getLogger(__name__)


async def parse_document_node(state: PipelineState) -> dict:
    """Parse uploaded document into raw blocks."""
    doc_refs = state.get("document_refs", [])
    if not doc_refs:
        return {"errors": [{"agent": "document_parser", "error": "No document references"}]}

    all_blocks = []
    for doc_path in doc_refs:
        # Determine MIME type from extension
        if doc_path.endswith(".pdf"):
            mime = "application/pdf"
        elif doc_path.endswith(".docx"):
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            continue

        result = parse_document(doc_path, mime)
        all_blocks.extend([b.model_dump() for b in result.raw_blocks])

    return {"raw_blocks": {"blocks": all_blocks}}


async def normalize_resume_node(state: PipelineState) -> dict:
    """Normalize raw blocks into ResumeSchema."""
    raw_blocks_data = state.get("raw_blocks", {})
    blocks_data = raw_blocks_data.get("blocks", []) if isinstance(raw_blocks_data, dict) else []

    if not blocks_data:
        return {"errors": [{"agent": "resume_normalizer", "error": "No raw blocks to normalize"}]}

    blocks = [RawBlock(**b) for b in blocks_data]
    llm = GeminiProvider()
    schema = await normalize_resume(blocks, llm)

    return {"resume_schema": schema.model_dump()}


async def analyze_jd_node(state: PipelineState) -> dict:
    """Analyze job description text."""
    jd_text = state.get("jd_raw", "")
    if not jd_text:
        return {"errors": [{"agent": "jd_analyzer", "error": "No job description provided"}]}

    llm = GeminiProvider()
    analysis = await analyze_job_description(jd_text, llm)

    return {"jd_analysis": analysis.model_dump()}


async def score_ats_node(state: PipelineState) -> dict:
    """Score resume against job description."""
    resume_data = state.get("resume_schema")
    jd_data = state.get("jd_analysis")

    if not resume_data or not jd_data:
        return {"errors": [{"agent": "ats_scorer", "error": "Missing resume or JD data"}]}

    resume = ResumeSchema.model_validate(resume_data)
    jd = JDAnalysis.model_validate(jd_data)
    llm = GeminiProvider()

    report = await score_resume(resume, jd, llm)

    return {"ats_report": report.model_dump()}


async def generate_resume_node(state: PipelineState) -> dict:
    """Generate tailored resume variant."""
    resume_data = state.get("resume_schema")
    ats_data = state.get("ats_report")

    if not resume_data or not ats_data:
        return {"errors": [{"agent": "resume_generator", "error": "Missing resume or ATS data"}]}

    resume = ResumeSchema.model_validate(resume_data)
    ats = ATSScoreReport.model_validate(ats_data)
    llm = GeminiProvider()
    settings = get_settings()

    gen_config = state.get("generation_config", {})
    variant = gen_config.get("variant", "CONSERVATIVE") if isinstance(gen_config, dict) else "CONSERVATIVE"

    tailored, file_path, pdf_path = await generate_resume(resume, ats, variant, llm, settings.storage_path)

    return {
        "generated_variants": [tailored.model_dump()],
        "generated_file_refs": [file_path, pdf_path],
    }
