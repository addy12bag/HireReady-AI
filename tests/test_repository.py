"""Tests for app/db/repository.py — uses in-memory SQLite."""
from app.db import repository


# ── Session CRUD ──────────────────────────────────────────────────

class TestSessionCRUD:
    async def test_create_session(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE", "user1")
        assert session.id is not None
        assert session.task_type == "FULL_PIPELINE"
        assert session.user_id == "user1"
        assert session.status == "INIT"

    async def test_create_session_default_user(self, db_session):
        session = await repository.create_session(db_session, "ATS_ONLY")
        assert session.user_id == "anonymous"

    async def test_get_session(self, db_session):
        created = await repository.create_session(db_session, "FULL_PIPELINE")
        found = await repository.get_session(db_session, created.id)
        assert found is not None
        assert found.id == created.id

    async def test_get_session_not_found(self, db_session):
        found = await repository.get_session(db_session, "nonexistent-id")
        assert found is None

    async def test_update_session_status(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        await repository.update_session_status(db_session, session.id, "PARSED")
        updated = await repository.get_session(db_session, session.id)
        assert updated.status == "PARSED"

    async def test_update_session_status_nonexistent(self, db_session):
        # Should not raise
        await repository.update_session_status(db_session, "nonexistent", "PARSED")


# ── Document CRUD ─────────────────────────────────────────────────

class TestDocumentCRUD:
    async def test_create_document(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        doc = await repository.create_document(
            db_session, session.id, "resume.pdf", "application/pdf", "/tmp/resume.pdf", 1024
        )
        assert doc.id is not None
        assert doc.filename == "resume.pdf"
        assert doc.mime_type == "application/pdf"
        assert doc.file_size_bytes == 1024


# ── Resume Schema CRUD ────────────────────────────────────────────

class TestResumeSchemaCRUD:
    async def test_save_and_get(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        schema_json = {"contact": {"name": "Jane"}}
        saved = await repository.save_resume_schema(db_session, session.id, schema_json, 0.9)
        assert saved.schema_json == schema_json
        assert saved.extraction_confidence == 0.9

        found = await repository.get_resume_schema(db_session, session.id)
        assert found is not None
        assert found.schema_json == schema_json

    async def test_upsert(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        await repository.save_resume_schema(db_session, session.id, {"v": 1}, 0.5)
        await repository.save_resume_schema(db_session, session.id, {"v": 2}, 0.8)
        found = await repository.get_resume_schema(db_session, session.id)
        assert found.schema_json == {"v": 2}
        assert found.extraction_confidence == 0.8

    async def test_get_not_found(self, db_session):
        assert await repository.get_resume_schema(db_session, "nope") is None


# ── JD Analysis CRUD ──────────────────────────────────────────────

class TestJDAnalysisCRUD:
    async def test_save_and_get(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        saved = await repository.save_jd_analysis(db_session, session.id, "raw text", {"k": "v"})
        assert saved.raw_text == "raw text"

        found = await repository.get_jd_analysis(db_session, session.id)
        assert found is not None
        assert found.analysis_json == {"k": "v"}

    async def test_upsert(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        await repository.save_jd_analysis(db_session, session.id, "v1", {"a": 1})
        await repository.save_jd_analysis(db_session, session.id, "v2", {"a": 2})
        found = await repository.get_jd_analysis(db_session, session.id)
        assert found.raw_text == "v2"


# ── ATS Report CRUD ───────────────────────────────────────────────

class TestATSReportCRUD:
    async def test_save_and_get(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        saved = await repository.save_ats_report(db_session, session.id, 85.0, "B", {"score": 85})
        assert saved.overall_score == 85.0
        assert saved.grade == "B"

        found = await repository.get_ats_report(db_session, session.id)
        assert found is not None
        assert found.report_json == {"score": 85}

    async def test_upsert(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        await repository.save_ats_report(db_session, session.id, 70.0, "C", {})
        await repository.save_ats_report(db_session, session.id, 90.0, "A", {})
        found = await repository.get_ats_report(db_session, session.id)
        assert found.overall_score == 90.0


# ── Generated Resume CRUD ─────────────────────────────────────────

class TestGeneratedResumeCRUD:
    async def test_save_and_get(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        saved = await repository.save_generated_resume(
            db_session, session.id, "CONSERVATIVE", {"v": 1}, "/tmp/resume.docx"
        )
        assert saved.variant == "CONSERVATIVE"
        assert saved.file_path == "/tmp/resume.docx"

        found = await repository.get_generated_resume(db_session, saved.id)
        assert found is not None

    async def test_get_resumes_list(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        await repository.save_generated_resume(db_session, session.id, "CONSERVATIVE", {})
        await repository.save_generated_resume(db_session, session.id, "AGGRESSIVE", {})
        resumes = await repository.get_generated_resumes(db_session, session.id)
        assert len(resumes) == 2

    async def test_get_resumes_empty(self, db_session):
        assert await repository.get_generated_resumes(db_session, "nope") == []


# ── Chat Message CRUD ─────────────────────────────────────────────

class TestChatMessageCRUD:
    async def test_save_and_get_history(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        await repository.save_chat_message(db_session, session.id, "user", "Hello")
        await repository.save_chat_message(db_session, session.id, "assistant", "Hi there")
        history = await repository.get_chat_history(db_session, session.id)
        assert len(history) == 2
        # Both messages should be present
        roles = {m.role for m in history}
        assert roles == {"user", "assistant"}
        contents = {m.content for m in history}
        assert contents == {"Hello", "Hi there"}

    async def test_chat_history_limit(self, db_session):
        session = await repository.create_session(db_session, "FULL_PIPELINE")
        for i in range(5):
            await repository.save_chat_message(db_session, session.id, "user", f"msg {i}")
        history = await repository.get_chat_history(db_session, session.id, limit=3)
        assert len(history) == 3

    async def test_chat_history_empty(self, db_session):
        assert await repository.get_chat_history(db_session, "nope") == []
