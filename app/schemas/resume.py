from pydantic import BaseModel


class Location(BaseModel):
    city: str | None = None
    state: str | None = None
    country: str | None = None


class Contact(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    location: Location | None = None


class Bullet(BaseModel):
    text: str
    has_metric: bool = False
    action_verb: str | None = None
    impact_score: float | None = None


class Experience(BaseModel):
    id: str
    company: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    bullets: list[Bullet] = []
    inferred_skills: list[str] = []


class Education(BaseModel):
    id: str
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None


class Skills(BaseModel):
    technical: list[str] = []
    soft: list[str] = []
    certifications: list[str] = []
    languages: list[str] = []


class Project(BaseModel):
    id: str
    name: str | None = None
    description: str | None = None
    technologies: list[str] = []
    url: str | None = None


class ResumeSchema(BaseModel):
    schema_version: str = "2.1"
    contact: Contact = Contact()
    summary: str | None = None
    experience: list[Experience] = []
    education: list[Education] = []
    skills: Skills = Skills()
    projects: list[Project] = []
    extraction_confidence: float = 1.0
    flagged_fields: list[str] = []
