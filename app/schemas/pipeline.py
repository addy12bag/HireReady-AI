from typing import Literal, TypedDict, Optional


class PipelineState(TypedDict, total=False):
    session_id: str
    user_id: str
    task_type: Literal["FULL_PIPELINE", "ATS_ONLY", "GENERATE_ONLY", "EXPLAIN"]

    # Document pipeline
    document_refs: list[str]
    raw_blocks: Optional[dict]
    resume_schema: Optional[dict]

    # JD pipeline
    jd_raw: Optional[str]
    jd_analysis: Optional[dict]

    # Scoring
    ats_report: Optional[dict]

    # Generation
    generation_config: Optional[dict]
    generated_variants: Optional[list[dict]]
    generated_file_refs: Optional[list[str]]

    # Chat
    chat_history: list[dict]

    # Control flow
    retry_counts: dict[str, int]
    errors: list[dict]
    pipeline_status: Literal["RUNNING", "DEGRADED", "COMPLETE", "FAILED"]
