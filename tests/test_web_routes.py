"""Tests for web routes (app/web/routes.py) — httpx client with mocked deps."""


# ── Landing Page ──────────────────────────────────────────────────

class TestLandingPage:
    async def test_index(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Resume AI" in resp.text


# ── Session Create ────────────────────────────────────────────────

class TestSessionCreate:
    async def test_create_session(self, client):
        resp = await client.post("/session/create", follow_redirects=False)
        assert resp.status_code == 200
        assert "HX-Redirect" in resp.headers


# ── Session Dashboard ─────────────────────────────────────────────

class TestSessionDashboard:
    async def test_valid_session(self, client):
        create_resp = await client.post("/session/create", follow_redirects=False)
        session_url = create_resp.headers.get("HX-Redirect", "")
        session_id = session_url.split("/")[-1]
        resp = await client.get(f"/session/{session_id}")
        assert resp.status_code == 200
        assert "Upload" in resp.text or "upload" in resp.text

    async def test_invalid_session_redirects(self, client):
        resp = await client.get("/session/nonexistent", follow_redirects=False)
        assert resp.status_code == 303


# ── Upload ────────────────────────────────────────────────────────

class TestUpload:
    async def test_upload_docx(self, client, tmp_path, monkeypatch):
        from app.storage.local import LocalFilesystemStorage
        from docx import Document
        import io

        create_resp = await client.post("/session/create", follow_redirects=False)
        session_url = create_resp.headers.get("HX-Redirect", "")
        session_id = session_url.split("/")[-1]

        doc = Document()
        doc.add_paragraph("Jane Doe\njane@example.com")
        buf = io.BytesIO()
        doc.save(buf)

        storage = LocalFilesystemStorage.__new__(LocalFilesystemStorage)
        storage.base_path = tmp_path
        monkeypatch.setattr("app.web.routes.get_storage", lambda: storage)

        resp = await client.post(
            f"/session/{session_id}/upload",
            files={"file": ("resume.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            follow_redirects=False,
        )
        assert resp.status_code == 200

    async def test_upload_no_file(self, client):
        create_resp = await client.post("/session/create", follow_redirects=False)
        session_url = create_resp.headers.get("HX-Redirect", "")
        session_id = session_url.split("/")[-1]
        resp = await client.post(f"/session/{session_id}/upload", follow_redirects=False)
        assert resp.status_code == 422


# ── Score ─────────────────────────────────────────────────────────

class TestScore:
    async def test_score_without_resume(self, client):
        create_resp = await client.post("/session/create", follow_redirects=False)
        session_url = create_resp.headers.get("HX-Redirect", "")
        session_id = session_url.split("/")[-1]
        resp = await client.post(
            f"/session/{session_id}/score",
            data={"job_description_text": "Python developer"},
            follow_redirects=False,
        )
        # FastAPI returns 422 for validation errors, 400 for business logic
        assert resp.status_code in (400, 422)


# ── Results ───────────────────────────────────────────────────────

class TestResults:
    async def test_results_without_ats(self, client):
        create_resp = await client.post("/session/create", follow_redirects=False)
        session_url = create_resp.headers.get("HX-Redirect", "")
        session_id = session_url.split("/")[-1]
        resp = await client.get(f"/session/{session_id}/results", follow_redirects=False)
        assert resp.status_code == 303


# ── Generate ──────────────────────────────────────────────────────

class TestGenerate:
    async def test_generate_without_resume(self, client):
        create_resp = await client.post("/session/create", follow_redirects=False)
        session_url = create_resp.headers.get("HX-Redirect", "")
        session_id = session_url.split("/")[-1]
        resp = await client.post(
            f"/session/{session_id}/generate",
            data={"variant": "CONSERVATIVE"},
            follow_redirects=False,
        )
        assert resp.status_code == 400


# ── Chat ──────────────────────────────────────────────────────────

class TestChat:
    async def test_chat_page(self, client):
        create_resp = await client.post("/session/create", follow_redirects=False)
        session_url = create_resp.headers.get("HX-Redirect", "")
        session_id = session_url.split("/")[-1]
        resp = await client.get(f"/session/{session_id}/chat")
        assert resp.status_code == 200
        assert "AI Resume Assistant" in resp.text

    async def test_send_message(self, client):
        create_resp = await client.post("/session/create", follow_redirects=False)
        session_url = create_resp.headers.get("HX-Redirect", "")
        session_id = session_url.split("/")[-1]
        resp = await client.post(
            f"/session/{session_id}/chat",
            data={"message": "Hello"},
            follow_redirects=False,
        )
        assert resp.status_code == 200
