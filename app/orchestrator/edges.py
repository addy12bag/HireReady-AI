from app.schemas.pipeline import PipelineState


def route_after_normalize(state: PipelineState) -> str:
    """After normalization: go to scoring if JD exists, else wait."""
    if state.get("jd_raw") and state.get("jd_analysis"):
        return "score"
    return "wait"


def route_after_jd(state: PipelineState) -> str:
    """After JD analysis: go to scoring if resume exists, else wait."""
    if state.get("resume_schema"):
        return "score"
    return "wait"
