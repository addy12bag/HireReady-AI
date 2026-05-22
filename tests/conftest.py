"""Shared test fixtures for resume-ai-platform."""
import pytest
import pytest_asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.models import Base
from app.llm.provider import LLMProvider
from app.schemas.resume import ResumeSchema, Contact, Experience, Bullet, Education, Skills
from app.schemas.job_description import JDAnalysis, JobMetadata, Requirements, HardRequirement
from app.schemas.ats_report import (
    ATSScoreReport, ScoreBreakdown, ScoreLayer, KeywordAnalysis, GapItem,
)


# ── Mock LLM Provider ────────────────────────────────────────────

class MockLLMProvider(LLMProvider):
    """Deterministic LLM provider for testing."""

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        return "Mock generated text response."

    async def generate_json(self, prompt: str, system: str = "", schema=None) -> dict:
        return {
            "contact": {"name": "Jane Doe", "email": "jane@example.com", "phone": "555-1234"},
            "summary": "Experienced software engineer with 5 years of experience.",
            "experience": [{
                "id": "exp_0",
                "company": "Acme Corp",
                "title": "Senior Engineer",
                "start_date": "2020-01",
                "end_date": "PRESENT",
                "location": "Remote",
                "bullets": [{"text": "Built scalable APIs serving 10M requests/day", "has_metric": True}],
                "inferred_skills": ["Python", "FastAPI"],
            }],
            "education": [{
                "id": "edu_0",
                "institution": "MIT",
                "degree": "BS",
                "field": "Computer Science",
                "start_date": "2016",
                "end_date": "2020",
                "gpa": "3.8",
            }],
            "skills": {
                "technical": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                "soft": ["Communication", "Leadership"],
                "certifications": [],
                "languages": ["English"],
            },
            "projects": [],
            # JD analysis fields
            "job_metadata": {
                "title": "Software Engineer",
                "company": "Acme",
                "seniority": "MID",
                "employment_type": "FULL_TIME",
                "location_type": "REMOTE",
            },
            "requirements": {
                "hard": [{"skill": "Python", "years": 3, "weight": 1.0, "mandatory": True}],
                "soft": [],
                "domain_knowledge": [],
            },
            "ats_keywords": ["Python", "API", "PostgreSQL"],
            "seniority_signals": [],
            "company_culture_signals": [],
            "jd_quality_score": 0.7,
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1 * (i + 1)] * 10 for i in range(len(texts))]


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


# ── Database Fixtures ─────────────────────────────────────────────

@pytest_asyncio.fixture
async def async_engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine):
    session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


# ── FastAPI App Fixtures ──────────────────────────────────────────

@pytest_asyncio.fixture
async def app(async_engine):
    from app.main import app as fastapi_app
    from app.deps import get_session

    session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_session] = override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c


# ── LLM Monkeypatch for Route Tests ──────────────────────────────

@pytest.fixture(autouse=True)
def mock_llm_provider(monkeypatch, mock_llm):
    """Override get_llm_provider in all route modules."""
    monkeypatch.setattr("app.web.routes.get_llm_provider", lambda: mock_llm)
    monkeypatch.setattr("app.api.routes.documents.get_llm_provider", lambda: mock_llm)
    monkeypatch.setattr("app.api.routes.scoring.get_llm_provider", lambda: mock_llm)
    monkeypatch.setattr("app.api.routes.generation.get_llm_provider", lambda: mock_llm)
    monkeypatch.setattr("app.api.routes.chat.get_llm_provider", lambda: mock_llm)


# ── Sample Data Factories ─────────────────────────────────────────

@pytest.fixture
def sample_resume_schema():
    return ResumeSchema(
        contact=Contact(name="Jane Doe", email="jane@example.com", phone="555-1234"),
        summary="Experienced software engineer with 5 years of experience.",
        experience=[
            Experience(
                id="exp_0",
                company="Acme Corp",
                title="Senior Engineer",
                start_date="2020-01",
                end_date="PRESENT",
                location="Remote",
                bullets=[
                    Bullet(text="Built scalable APIs serving 10M requests/day", has_metric=True),
                    Bullet(text="Led team of 4 engineers", has_metric=False),
                ],
                inferred_skills=["Python", "FastAPI"],
            )
        ],
        education=[
            Education(id="edu_0", institution="MIT", degree="BS", field="Computer Science", start_date="2016", end_date="2020", gpa="3.8")
        ],
        skills=Skills(technical=["Python", "FastAPI", "PostgreSQL", "Docker"], soft=["Communication"]),
        projects=[],
    )


@pytest.fixture
def sample_jd_analysis():
    return JDAnalysis(
        job_metadata=JobMetadata(
            title="Software Engineer",
            company="Acme",
            seniority="MID",
            employment_type="FULL_TIME",
            location_type="REMOTE",
        ),
        requirements=Requirements(
            hard=[
                HardRequirement(skill="Python", years=3, weight=1.0, mandatory=True),
                HardRequirement(skill="FastAPI", years=2, weight=0.8, mandatory=True),
                HardRequirement(skill="PostgreSQL", years=2, weight=0.7, mandatory=False),
            ],
            soft=["Communication"],
            domain_knowledge=["Web Development"],
        ),
        ats_keywords=["Python", "FastAPI", "PostgreSQL", "REST API"],
        seniority_signals=["team lead"],
        company_culture_signals=[],
        jd_quality_score=0.7,
    )


@pytest.fixture
def sample_ats_report():
    return ATSScoreReport(
        overall_score=75.0,
        grade="B",
        score_breakdown=ScoreBreakdown(
            keyword_exact_match=ScoreLayer(score=80.0, weight=0.30, weighted_score=24.0),
            semantic_similarity=ScoreLayer(score=70.0, weight=0.25, weighted_score=17.5),
            experience_alignment=ScoreLayer(score=75.0, weight=0.20, weighted_score=15.0),
            skills_coverage=ScoreLayer(score=80.0, weight=0.15, weighted_score=12.0),
            formatting_compliance=ScoreLayer(score=100.0, weight=0.05, weighted_score=5.0),
            section_completeness=ScoreLayer(score=85.0, weight=0.05, weighted_score=4.25),
        ),
        keyword_analysis=KeywordAnalysis(
            matched=["Python", "FastAPI"],
            missing_critical=["PostgreSQL"],
            missing_preferred=["REST API"],
        ),
        gap_analysis=[
            GapItem(gap="PostgreSQL", severity="HIGH", suggestion="Add PostgreSQL experience", evidence_from_jd="Required 2 years"),
        ],
        formatting_issues=[],
        estimated_pass_rate=0.72,
    )


@pytest.fixture
def sample_resume_blocks():
    from app.schemas.blocks import RawBlock, BoundingBox
    return [
        RawBlock(
            block_id="b1",
            type="TEXT",
            content="Jane Doe\njane@example.com\n555-1234",
            bbox=BoundingBox(x0=0, y0=0, x1=100, y1=30),
            page=1,
        ),
        RawBlock(
            block_id="b2",
            type="TEXT",
            content="Experience\nSenior Engineer at Acme Corp (2020-Present)\nBuilt scalable APIs",
            bbox=BoundingBox(x0=0, y0=40, x1=100, y1=80),
            page=1,
        ),
    ]


@pytest.fixture
def sample_jd_text():
    return """Software Engineer - Acme Corp

We are looking for a Software Engineer with 3+ years of Python experience.
Must have experience with FastAPI and PostgreSQL.

Requirements:
- 3+ years Python
- 2+ years FastAPI
- Experience with REST APIs
- Good communication skills

Remote position, full-time."""
