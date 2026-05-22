from pydantic import BaseModel


class ScoringRequest(BaseModel):
    session_id: str
    job_description_text: str


class ScoringResponse(BaseModel):
    session_id: str
    overall_score: float
    grade: str
    report: dict
