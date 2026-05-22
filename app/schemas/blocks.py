from pydantic import BaseModel


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class RawBlock(BaseModel):
    block_id: str
    type: str  # TEXT, TABLE, HEADER, IMAGE
    content: str
    bbox: BoundingBox | None = None
    page: int = 1
    confidence: float = 1.0


class DocumentMetadata(BaseModel):
    page_count: int = 1
    has_columns: bool = False
    detected_language: str = "en"


class ExtractionResult(BaseModel):
    status: str  # SUCCESS, PARTIAL, FAILED
    extraction_method: str  # PDFPLUMBER, DOCX_PARSER
    raw_blocks: list[RawBlock]
    document_metadata: DocumentMetadata
