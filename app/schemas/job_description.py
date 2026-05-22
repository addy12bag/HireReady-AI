from pydantic import BaseModel


class HardRequirement(BaseModel):
    skill: str
    years: int | None = None
    weight: float = 1.0
    mandatory: bool = True


class Requirements(BaseModel):
    hard: list[HardRequirement] = []
    soft: list[str] = []
    domain_knowledge: list[str] = []


class JobMetadata(BaseModel):
    title: str | None = None
    company: str | None = None
    seniority: str | None = None  # ENTRY, MID, SENIOR, LEAD, EXECUTIVE
    employment_type: str | None = None  # FULL_TIME, PART_TIME, CONTRACT
    location_type: str | None = None  # REMOTE, HYBRID, ONSITE


class JDAnalysis(BaseModel):
    job_metadata: JobMetadata = JobMetadata()
    requirements: Requirements = Requirements()
    ats_keywords: list[str] = []
    seniority_signals: list[str] = []
    company_culture_signals: list[str] = []
    jd_quality_score: float = 0.5
