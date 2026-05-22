"""Build ATS-friendly PDF resumes matching a clean LaTeX-inspired layout using fpdf2."""
from fpdf import FPDF

from app.schemas.resume import ResumeSchema


class ResumePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    @staticmethod
    def _sanitize(text: str) -> str:
        """Replace Unicode characters with ASCII equivalents for Helvetica."""
        replacements = {
            "\u2013": "-",   # en-dash
            "\u2014": "-",   # em-dash
            "\u2018": "'",   # left single quote
            "\u2019": "'",   # right single quote
            "\u201c": '"',   # left double quote
            "\u201d": '"',   # right double quote
            "\u2026": "...",  # ellipsis
            "\u00b7": "-",   # middle dot
            "\u2022": "-",   # bullet
            "\u00a0": " ",   # non-breaking space
            "\u00b0": " deg ",  # degree
        }
        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)
        return text

    def _section_heading(self, text: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 5, self._sanitize(text.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def _tabular_line(self, left: str, right: str,
                       left_bold: bool = True, left_italic: bool = False,
                       right_italic: bool = False, font_size: int = 9):
        y = self.get_y()
        col_w = (self.w - self.l_margin - self.r_margin) / 2

        # Left column
        self.set_xy(self.l_margin, y)
        style = ""
        if left_bold:
            style += "B"
        if left_italic:
            style += "I"
        self.set_font("Helvetica", style if style else "", font_size)
        self.cell(col_w, 5, self._sanitize(left))

        # Right column
        self.set_xy(self.l_margin + col_w, y)
        style = "I" if right_italic else ""
        self.set_font("Helvetica", style if style else "", font_size)
        self.cell(col_w, 5, self._sanitize(right), align="R")

        self.ln(5)

    def _bullet(self, text: str, font_size: int = 9):
        self.set_font("Helvetica", "", font_size)
        x = self.l_margin + 5
        self.set_x(x)
        bullet_w = self.get_string_width("- ")
        self.cell(bullet_w, 4.5, "- ")
        max_w = self.w - self.r_margin - x - bullet_w
        self.multi_cell(max_w, 4.5, self._sanitize(text))
        self.ln(0.5)

    def _wrap_text(self, text: str, max_width: float, font_size: int = 9):
        """Wrap text to fit within max_width, return lines."""
        self.set_font("Helvetica", "", font_size)
        words = text.split(" ")
        lines = []
        current_line = ""
        for word in words:
            test = current_line + (" " if current_line else "") + word
            if self.get_string_width(test) > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)
        return lines


def build_pdf(resume: ResumeSchema, output_path: str | None = None) -> bytes:
    """Build an ATS-safe PDF matching a clean LaTeX-inspired layout."""
    pdf = ResumePDF()
    pdf.add_page()

    # Margins
    pdf.set_margins(12, 10, 12)

    contact = resume.contact
    name_text = contact.name or "Resume"
    content_w = pdf.w - pdf.l_margin - pdf.r_margin

    # ── Header: Name + Contact ──
    y = pdf.get_y()

    # Name (left)
    pdf.set_xy(pdf.l_margin, y)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(content_w / 2, 7, pdf._sanitize(name_text))

    # Email + Phone (right)
    pdf.set_xy(pdf.l_margin + content_w / 2, y)
    pdf.set_font("Helvetica", "", 9)
    contact_lines = []
    if contact.email:
        contact_lines.append(f"Email: {contact.email}")
    if contact.phone:
        contact_lines.append(f"Mobile: {contact.phone}")
    for i, line in enumerate(contact_lines):
        pdf.set_xy(pdf.l_margin + content_w / 2, y + i * 4.5)
        pdf.cell(content_w / 2, 4.5, pdf._sanitize(line), align="R")

    max_y = y + max(len(contact_lines) * 4.5, 7)
    pdf.set_y(max_y)

    # Links line
    link_parts = []
    if contact.github:
        link_parts.append(f"Github: {contact.github}")
    if contact.linkedin:
        link_parts.append(f"LinkedIn: {contact.linkedin}")
    loc_parts = []
    if contact.location and contact.location.city:
        loc_parts.append(contact.location.city)
    if contact.location and contact.location.country:
        loc_parts.append(contact.location.country)

    if link_parts:
        y = pdf.get_y()
        pdf.set_xy(pdf.l_margin, y)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(content_w / 2, 4.5, pdf._sanitize(link_parts[0]))
        if loc_parts:
            pdf.set_xy(pdf.l_margin + content_w / 2, y)
            pdf.cell(content_w / 2, 4.5, pdf._sanitize(", ".join(loc_parts)), align="R")
        pdf.ln(5)

    pdf.ln(2)

    # ── Summary ──
    if resume.summary:
        pdf._section_heading("Professional Summary")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 4.5, pdf._sanitize(resume.summary))
        pdf.ln(1)

    # ── Education ──
    if resume.education:
        pdf._section_heading("Education")
        for edu in resume.education:
            pdf._tabular_line(
                edu.institution or "",
                "",
                left_bold=True, font_size=9,
            )
            degree_parts = []
            if edu.degree and edu.field:
                base = f"{edu.degree} - {edu.field}"
                if edu.gpa:
                    base += f";  GPA: {edu.gpa}"
                degree_parts.append(base)
            elif edu.degree:
                degree_parts.append(edu.degree)

            date_parts = []
            if edu.start_date:
                date_parts.append(edu.start_date)
            if edu.end_date:
                date_parts.append(edu.end_date)

            if degree_parts:
                pdf._tabular_line(
                    degree_parts[0],
                    " - ".join(date_parts),
                    left_bold=False, left_italic=True,
                    right_italic=True, font_size=9,
                )

    # ── Skills Summary ──
    skills = resume.skills
    has_skills = any([skills.technical, skills.soft, skills.languages, skills.certifications])
    if has_skills:
        pdf._section_heading("Skills Summary")
        if skills.technical:
            pdf._tabular_line("Languages/Technologies", ", ".join(skills.technical), left_bold=True, font_size=9)
        if skills.soft:
            pdf._tabular_line("Soft Skills", ", ".join(skills.soft), left_bold=True, font_size=9)
        if skills.languages:
            pdf._tabular_line("Spoken Languages", ", ".join(skills.languages), left_bold=True, font_size=9)
        if skills.certifications:
            pdf._tabular_line("Certifications", ", ".join(skills.certifications), left_bold=True, font_size=9)

    # ── Experience ──
    if resume.experience:
        pdf._section_heading("Experience")
        for exp in resume.experience:
            pdf._tabular_line(
                exp.company or "",
                exp.location or "",
                left_bold=True, font_size=9,
            )
            date_parts = []
            if exp.start_date:
                date_parts.append(exp.start_date)
            if exp.end_date:
                date_parts.append(exp.end_date)

            pdf._tabular_line(
                exp.title or "",
                " - ".join(date_parts),
                left_bold=False, left_italic=True,
                right_italic=True, font_size=9,
            )
            for bullet in exp.bullets:
                pdf._bullet(bullet.text, font_size=9)

    # ── Projects ──
    if resume.projects:
        pdf._section_heading("Projects")
        for proj in resume.projects:
            name = proj.name or "Project"
            if proj.technologies:
                name += f" ({', '.join(proj.technologies)})"

            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, pdf._sanitize(name), new_x="LMARGIN", new_y="NEXT")

            if proj.description:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_x(pdf.l_margin + 5)
                max_w = content_w - 5
                lines = pdf._wrap_text(pdf._sanitize(proj.description), max_w, 9)
                for line in lines:
                    pdf.set_x(pdf.l_margin + 5)
                    pdf.cell(max_w, 4.5, line, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)

            if proj.url:
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(0, 0, 180)
                pdf.set_x(pdf.l_margin + 5)
                pdf.cell(0, 4, pdf._sanitize(f"URL: {proj.url}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)
                pdf.ln(1)

    # ── Certifications & Achievements ──
    if skills.certifications:
        pdf._section_heading("Certifications & Achievements")
        for cert in skills.certifications:
            pdf._bullet(pdf._sanitize(cert), font_size=9)

    # Output
    pdf_bytes = pdf.output()

    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes
