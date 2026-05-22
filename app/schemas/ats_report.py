from pydantic import BaseModel


class ScoreLayer(BaseModel):
    score: float
    weight: float
    weighted_score: float


class ScoreBreakdown(BaseModel):
    keyword_exact_match: ScoreLayer
    semantic_similarity: ScoreLayer
    experience_alignment: ScoreLayer
    skills_coverage: ScoreLayer
    formatting_compliance: ScoreLayer
    section_completeness: ScoreLayer


class KeywordAnalysis(BaseModel):
    matched: list[str] = []
    missing_critical: list[str] = []
    missing_preferred: list[str] = []
    over_represented: list[str] = []


class GapItem(BaseModel):
    gap: str
    severity: str  # HIGH, MEDIUM, LOW
    suggestion: str
    evidence_from_jd: str | None = None


class ATSScoreReport(BaseModel):
    overall_score: float
    grade: str  # A, B, C, D, F
    score_breakdown: ScoreBreakdown
    keyword_analysis: KeywordAnalysis
    gap_analysis: list[GapItem] = []
    formatting_issues: list[str] = []
    estimated_pass_rate: float = 0.0
