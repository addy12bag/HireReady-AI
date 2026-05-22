from pydantic import BaseModel


class GenerationRequest(BaseModel):
    session_id: str
    variant: str = "CONSERVATIVE"


class GenerationResponse(BaseModel):
    generated_resume_id: str
    session_id: str
    variant: str
    download_url: str | None = None
