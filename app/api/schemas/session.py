from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    task_type: str = "FULL_PIPELINE"
    user_id: str = "anonymous"


class SessionCreateResponse(BaseModel):
    session_id: str
    task_type: str
    status: str


class SessionDetailResponse(BaseModel):
    session_id: str
    user_id: str
    task_type: str
    status: str
    has_resume: bool = False
    has_jd: bool = False
    has_ats_report: bool = False
