"""Tests for app/utils/nlp.py — pure functions, no mocking needed."""
from app.utils.nlp import normalize_skill, parse_date, extract_emails, extract_phones, extract_links


# ── normalize_skill ───────────────────────────────────────────────

class TestNormalizeSkill:
    def test_exact_taxonomy_match(self):
        assert normalize_skill("postgres") == "PostgreSQL"
        assert normalize_skill("postgresql") == "PostgreSQL"
        assert normalize_skill("reactjs") == "React"
        assert normalize_skill("node.js") == "Node.js"
        assert normalize_skill("python3") == "Python"
        assert normalize_skill("k8s") == "Kubernetes"
        assert normalize_skill("aws") == "AWS"

    def test_case_insensitive(self):
        assert normalize_skill("POSTGRES") == "PostgreSQL"
        assert normalize_skill("  Python  ") == "Python"

    def test_fuzzy_match(self):
        # Close enough to trigger fuzzy match
        assert normalize_skill("postgrse") == "PostgreSQL"

    def test_unknown_skill_title_cased(self):
        assert normalize_skill("django") == "Django"
        assert normalize_skill("flask") == "Flask"

    def test_empty_string(self):
        result = normalize_skill("")
        assert result == ""


# ── parse_date ────────────────────────────────────────────────────

class TestParseDate:
    def test_present_variants(self):
        assert parse_date("present") == "PRESENT"
        assert parse_date("current") == "PRESENT"
        assert parse_date("now") == "PRESENT"
        assert parse_date("PRESENT") == "PRESENT"

    def test_none_returns_present(self):
        assert parse_date(None) == "PRESENT"

    def test_standard_date_format(self):
        assert parse_date("Jan 2020") == "2020-01"
        assert parse_date("March 2019") == "2019-03"

    def test_iso_format_passthrough(self):
        assert parse_date("2020-01") == "2020-01"

    def test_unparseable_returns_original(self):
        assert parse_date("sometime ago") == "sometime ago"


# ── extract_emails ────────────────────────────────────────────────

class TestExtractEmails:
    def test_single_email(self):
        assert extract_emails("Contact: jane@example.com") == ["jane@example.com"]

    def test_multiple_emails(self):
        emails = extract_emails("a@b.com and c@d.org")
        assert len(emails) == 2

    def test_no_emails(self):
        assert extract_emails("no emails here") == []

    def test_email_in_sentence(self):
        emails = extract_emails("Send resume to hiring@company.co.uk today")
        assert "hiring@company.co.uk" in emails


# ── extract_phones ────────────────────────────────────────────────

class TestExtractPhones:
    def test_us_format(self):
        phones = extract_phones("Call 555-123-4567")
        assert any("555" in p for p in phones)

    def test_no_phones(self):
        assert extract_phones("no phones") == []


# ── extract_links ─────────────────────────────────────────────────

class TestExtractLinks:
    def test_linkedin_url(self):
        result = extract_links("linkedin.com/in/janedoe")
        assert result["linkedin"] == "linkedin.com/in/janedoe"

    def test_github_url(self):
        result = extract_links("github.com/janedoe")
        assert result["github"] == "github.com/janedoe"

    def test_both_urls(self):
        result = extract_links("linkedin.com/in/jane and github.com/janedoe")
        assert result["linkedin"] is not None
        assert result["github"] is not None

    def test_neither(self):
        result = extract_links("no links here")
        assert result["linkedin"] is None
        assert result["github"] is None
