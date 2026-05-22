from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    session_id: str
    filename: str
    mime_type: str
    blocks_extracted: int
    status: str
