import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, BigInteger, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_col(primary_key=False, **kwargs):
    if primary_key:
        return mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), **kwargs)
    return mapped_column(String(36), **kwargs)


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = _uuid_col(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), default="anonymous")
    task_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="INIT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["DocumentModel"]] = relationship(back_populates="session")
    resume_schema: Mapped["ResumeSchemaModel | None"] = relationship(back_populates="session")
    jd_analysis: Mapped["JDAnalysisModel | None"] = relationship(back_populates="session")
    ats_report: Mapped["ATSReportModel | None"] = relationship(back_populates="session")
    generated_resumes: Mapped[list["GeneratedResumeModel"]] = relationship(back_populates="session")
    chat_messages: Mapped[list["ChatMessageModel"]] = relationship(back_populates="session")


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[str] = _uuid_col(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    filename: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_path: Mapped[str] = mapped_column(String(1000))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["SessionModel"] = relationship(back_populates="documents")


class ResumeSchemaModel(Base):
    __tablename__ = "resume_schemas"

    id: Mapped[str] = _uuid_col(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), unique=True)
    schema_json: Mapped[dict] = mapped_column(JSON)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["SessionModel"] = relationship(back_populates="resume_schema")


class JDAnalysisModel(Base):
    __tablename__ = "jd_analyses"

    id: Mapped[str] = _uuid_col(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), unique=True)
    raw_text: Mapped[str] = mapped_column(Text)
    analysis_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["SessionModel"] = relationship(back_populates="jd_analysis")


class ATSReportModel(Base):
    __tablename__ = "ats_reports"

    id: Mapped[str] = _uuid_col(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), unique=True)
    overall_score: Mapped[float] = mapped_column(Float)
    grade: Mapped[str] = mapped_column(String(2))
    report_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["SessionModel"] = relationship(back_populates="ats_report")


class GeneratedResumeModel(Base):
    __tablename__ = "generated_resumes"

    id: Mapped[str] = _uuid_col(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    variant: Mapped[str] = mapped_column(String(50))
    schema_json: Mapped[dict] = mapped_column(JSON)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["SessionModel"] = relationship(back_populates="generated_resumes")


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = _uuid_col(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["SessionModel"] = relationship(back_populates="chat_messages")
