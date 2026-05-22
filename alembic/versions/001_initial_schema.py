"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, server_default="anonymous"),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="INIT"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "resume_schemas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), unique=True, nullable=False),
        sa.Column("schema_json", postgresql.JSONB, nullable=False),
        sa.Column("extraction_confidence", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "jd_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), unique=True, nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("analysis_json", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ats_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), unique=True, nullable=False),
        sa.Column("overall_score", sa.Float, nullable=False),
        sa.Column("grade", sa.String(5), nullable=False),
        sa.Column("report_json", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "generated_resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("variant", sa.String(50), nullable=False),
        sa.Column("schema_json", postgresql.JSONB, nullable=False),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata_json", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("generated_resumes")
    op.drop_table("ats_reports")
    op.drop_table("jd_analyses")
    op.drop_table("resume_schemas")
    op.drop_table("documents")
    op.drop_table("sessions")
