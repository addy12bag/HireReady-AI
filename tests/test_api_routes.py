"""Tests for API routes (app/api/routes/) — httpx client with mocked deps."""


# ── Health ────────────────────────────────────────────────────────

class TestHealth:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


# ── Sessions API ──────────────────────────────────────────────────

class TestSessionsAPI:
    async def test_create_session(self, client):
        resp = await client.post("/sessions", json={"task_type": "FULL_PIPELINE"})
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["task_type"] == "FULL_PIPELINE"
        assert data["status"] == "INIT"

    async def test_get_session(self, client):
        # Create via API so it's in the same DB context
        create_resp = await client.post("/sessions", json={"task_type": "FULL_PIPELINE"})
        session_id = create_resp.json()["session_id"]
        resp = await client.get(f"/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id

    async def test_get_session_not_found(self, client):
        resp = await client.get("/sessions/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_get_session_invalid_uuid(self, client):
        resp = await client.get("/sessions/not-a-uuid")
        assert resp.status_code == 400


# ── Documents API ─────────────────────────────────────────────────

class TestDocumentsAPI:
    async def test_upload_docx(self, client, tmp_path, monkeypatch):
        from app.storage.local import LocalFilesystemStorage
        from docx import Document
        import io

        create_resp = await client.post("/sessions", json={"task_type": "FULL_PIPELINE"})
        session_id = create_resp.json()["session_id"]

        doc = Document()
        doc.add_paragraph("Jane Doe\njane@example.com\nSenior Engineer at Acme")
        buf = io.BytesIO()
        doc.save(buf)

        storage = LocalFilesystemStorage.__new__(LocalFilesystemStorage)
        storage.base_path = tmp_path
        monkeypatch.setattr("app.api.routes.documents.get_storage", lambda: storage)

        resp = await client.post(
            "/documents/upload",
            data={"session_id": session_id},
            files={"file": ("resume.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["filename"] == "resume.docx"

    async def test_upload_invalid_session(self, client):
        resp = await client.post(
            "/documents/upload",
            data={"session_id": "00000000-0000-0000-0000-000000000000"},
            files={"file": ("resume.pdf", b"fake", "application/pdf")},
        )
        assert resp.status_code == 404

    async def test_upload_unsupported_type(self, client):
        create_resp = await client.post("/sessions", json={"task_type": "FULL_PIPELINE"})
        session_id = create_resp.json()["session_id"]
        resp = await client.post(
            "/documents/upload",
            data={"session_id": session_id},
            files={"file": ("image.png", b"fake", "image/png")},
        )
        assert resp.status_code == 400


# ── Scoring API ───────────────────────────────────────────────────

class TestScoringAPI:
    async def test_score_without_resume(self, client):
        create_resp = await client.post("/sessions", json={"task_type": "FULL_PIPELINE"})
        session_id = create_resp.json()["session_id"]
        resp = await client.post("/scoring/analyze", json={
            "session_id": session_id,
            "job_description_text": "Python developer needed",
        })
        assert resp.status_code == 400

    async def test_score_invalid_uuid(self, client):
        resp = await client.post("/scoring/analyze", json={
            "session_id": "bad-uuid",
            "job_description_text": "Python developer",
        })
        assert resp.status_code == 400


# ── Generation API ────────────────────────────────────────────────

class TestGenerationAPI:
    async def test_generate_no_resume(self, client):
        create_resp = await client.post("/sessions", json={"task_type": "FULL_PIPELINE"})
        session_id = create_resp.json()["session_id"]
        resp = await client.post("/generation/generate", json={
            "session_id": session_id,
            "variant": "CONSERVATIVE",
        })
        assert resp.status_code == 400

    async def test_generate_invalid_uuid(self, client):
        resp = await client.post("/generation/generate", json={
            "session_id": "bad-uuid",
            "variant": "CONSERVATIVE",
        })
        assert resp.status_code == 400


# ── Chat API ──────────────────────────────────────────────────────

class TestChatAPI:
    async def test_chat_message(self, client):
        create_resp = await client.post("/sessions", json={"task_type": "FULL_PIPELINE"})
        session_id = create_resp.json()["session_id"]
        resp = await client.post("/chat/message", json={
            "session_id": session_id,
            "message": "Hello",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert data["session_id"] == session_id

    async def test_chat_invalid_uuid(self, client):
        resp = await client.post("/chat/message", json={
            "session_id": "bad-uuid",
            "message": "Hello",
        })
        assert resp.status_code == 400

    async def test_chat_session_not_found(self, client):
        resp = await client.post("/chat/message", json={
            "session_id": "00000000-0000-0000-0000-000000000000",
            "message": "Hello",
        })
        assert resp.status_code == 404
