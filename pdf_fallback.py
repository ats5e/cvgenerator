from __future__ import annotations

from pathlib import Path

try:
    from fpdf import FPDF
except ImportError:  # pragma: no cover - optional runtime dependency
    FPDF = None


PAGE_WIDTH = 210
PAGE_HEIGHT = 297
LEFT_MARGIN = 14
RIGHT_MARGIN = 14
TOP_MARGIN = 14

SIGNATURE = {
    "bg": (13, 26, 44),
    "panel": (241, 233, 223),
    "panel_alt": (248, 244, 238),
    "accent": (226, 181, 128),
    "accent_dark": (128, 90, 54),
    "text": (25, 31, 40),
    "muted": (96, 105, 118),
    "line": (213, 199, 184),
    "white": (249, 244, 238),
}

PLAIN = {
    "bg": (255, 255, 255),
    "panel": (248, 249, 251),
    "panel_alt": (255, 255, 255),
    "accent": (51, 78, 114),
    "accent_dark": (35, 47, 62),
    "text": (27, 31, 38),
    "muted": (106, 112, 122),
    "line": (218, 223, 230),
    "white": (255, 255, 255),
}

TEXT_REPLACEMENTS = str.maketrans({
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2026": "...",
    "\u00a0": " ",
    "\u2022": "-",
})


def ensure_fpdf() -> None:
    if FPDF is None:
        raise RuntimeError(
            "Chrome PDF rendering is unavailable and fpdf2 is not installed. "
            "Add fpdf2 to the deployment dependencies."
        )


def pdf_text(value: object) -> str:
    text = str(value or "").translate(TEXT_REPLACEMENTS)
    return text.encode("latin-1", "replace").decode("latin-1")


class StyledPDF(FPDF if FPDF is not None else object):
    def footer(self) -> None:  # pragma: no cover - rendering only
        self.set_y(-10)
        self.set_draw_color(210, 214, 220)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_y(-8)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(128, 134, 144)
        self.cell(0, 4, pdf_text(f"Page {self.page_no()}"), 0, 0, "R")


def _theme(options: dict) -> dict:
    if options.get("design_style") == "plain":
        return PLAIN
    return SIGNATURE


def _setup_pdf() -> StyledPDF:
    ensure_fpdf()
    pdf = StyledPDF("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(LEFT_MARGIN, TOP_MARGIN, RIGHT_MARGIN)
    pdf.set_title("Du-Toit Griesel")
    pdf.set_author("Du-Toit Griesel")
    pdf.add_page()
    return pdf


def _ensure_space(pdf: StyledPDF, height: float) -> None:
    if pdf.get_y() + height <= pdf.page_break_trigger:
        return
    pdf.add_page()


def _section_heading(pdf: StyledPDF, title: str, theme: dict) -> None:
    _ensure_space(pdf, 14)
    pdf.ln(1.5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*theme["accent_dark"])
    pdf.cell(0, 6, pdf_text(title.upper()), ln=1)
    pdf.set_draw_color(*theme["line"])
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)


def _draw_header(
    pdf: StyledPDF,
    profile: dict,
    role_line: str,
    tagline: str,
    contact_line: str,
    options: dict,
    image_path: Path,
    theme: dict,
) -> None:
    if options.get("design_style") == "plain":
        pdf.set_fill_color(*theme["white"])
        pdf.set_text_color(*theme["text"])
        pdf.set_font("Times", "B", 27)
        pdf.cell(0, 10, pdf_text(f"{profile['first_name']} {profile['last_name']}"), ln=1)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*theme["accent"])
        pdf.cell(0, 6, pdf_text(role_line), ln=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*theme["muted"])
        pdf.multi_cell(0, 5, pdf_text(tagline))
        pdf.multi_cell(0, 5, pdf_text(contact_line))
        if options.get("include_photo") and image_path.exists():
            pdf.image(str(image_path), x=pdf.w - 34, y=10, w=20, h=20)
        pdf.ln(4)
        pdf.set_draw_color(*theme["line"])
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(5)
        return

    pdf.set_fill_color(*theme["bg"])
    pdf.rect(0, 0, PAGE_WIDTH, 44, "F")
    pdf.set_xy(LEFT_MARGIN, 12)
    pdf.set_text_color(*theme["white"])
    pdf.set_font("Times", "B", 29)
    pdf.cell(140, 10, pdf_text(f"{profile['first_name']} {profile['last_name']}"), ln=1)
    pdf.set_x(LEFT_MARGIN)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*theme["accent"])
    pdf.cell(110, 5, pdf_text(role_line), ln=1)
    pdf.set_x(LEFT_MARGIN)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(223, 228, 235)
    pdf.cell(0, 5, pdf_text(tagline), ln=1)
    pdf.set_x(LEFT_MARGIN)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(146, 4.6, pdf_text(contact_line))
    if options.get("include_photo") and image_path.exists():
        pdf.image(str(image_path), x=168, y=10, w=25, h=25)
    pdf.set_y(50)


def _draw_stats(pdf: StyledPDF, stats: list[dict], options: dict, theme: dict) -> None:
    if not options.get("show_highlight_strip"):
        return
    _ensure_space(pdf, 24)
    box_gap = 4
    box_width = (PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN - (box_gap * 2)) / 3
    start_y = pdf.get_y()
    for index, stat in enumerate(stats[:3]):
        x = LEFT_MARGIN + index * (box_width + box_gap)
        pdf.set_fill_color(*theme["panel"])
        pdf.set_draw_color(*theme["line"])
        pdf.rect(x, start_y, box_width, 18, "DF")
        pdf.set_xy(x + 3, start_y + 2.5)
        pdf.set_font("Times", "B", 18)
        pdf.set_text_color(*theme["accent_dark"])
        pdf.cell(box_width - 6, 6, pdf_text(stat["number"]), ln=1)
        pdf.set_x(x + 3)
        pdf.set_font("Helvetica", "", 8.4)
        pdf.set_text_color(*theme["muted"])
        pdf.multi_cell(box_width - 6, 3.8, pdf_text(stat["label"]))
    pdf.set_y(start_y + 22)


def _summary_block(pdf: StyledPDF, summary: str, theme: dict) -> None:
    _section_heading(pdf, "Profile", theme)
    _ensure_space(pdf, 20)
    pdf.set_fill_color(*theme["panel_alt"])
    pdf.set_draw_color(*theme["line"])
    start_x = pdf.l_margin
    start_y = pdf.get_y()
    width = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.rect(start_x, start_y, width, 18, "DF")
    pdf.set_xy(start_x + 4, start_y + 3)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*theme["text"])
    pdf.multi_cell(width - 8, 5.2, pdf_text(summary))
    used_height = max(18, pdf.get_y() - start_y + 3)
    if used_height > 18:
        pdf.set_fill_color(*theme["panel_alt"])
        pdf.set_draw_color(*theme["line"])
        pdf.rect(start_x, start_y, width, used_height, "D")
    pdf.ln(2)


def _skills_block(pdf: StyledPDF, skills: list[str], theme: dict) -> None:
    _section_heading(pdf, "Core Skills", theme)
    box_gap = 4
    box_width = (pdf.w - pdf.l_margin - pdf.r_margin - box_gap) / 2
    box_height = 10
    start_y = pdf.get_y()
    for index, skill in enumerate(skills):
        _ensure_space(pdf, box_height + 2)
        row = index // 2
        col = index % 2
        x = pdf.l_margin + col * (box_width + box_gap)
        y = start_y + row * (box_height + 3)
        if y + box_height > pdf.page_break_trigger:
            pdf.add_page()
            _section_heading(pdf, "Core Skills (Cont.)", theme)
            start_y = pdf.get_y()
            row = 0
            x = pdf.l_margin + col * (box_width + box_gap)
            y = start_y
        pdf.set_fill_color(*theme["panel"])
        pdf.set_draw_color(*theme["line"])
        pdf.rect(x, y, box_width, box_height, "DF")
        pdf.set_xy(x + 3, y + 2.2)
        pdf.set_font("Helvetica", "", 9.2)
        pdf.set_text_color(*theme["text"])
        pdf.multi_cell(box_width - 6, 4, pdf_text(skill))
    rows = max(1, (len(skills) + 1) // 2)
    pdf.set_y(start_y + rows * (box_height + 3))


def _experience_block(pdf: StyledPDF, experience: list[dict], theme: dict) -> None:
    _section_heading(pdf, "Experience", theme)
    for index, job in enumerate(experience):
        _ensure_space(pdf, 24)
        if index:
            pdf.ln(1)
        title_y = pdf.get_y()
        pdf.set_font("Helvetica", "B", 11.5)
        pdf.set_text_color(*theme["text"])
        pdf.cell(120, 6, pdf_text(job["title"]), 0, 0)
        pdf.set_font("Helvetica", "", 9.4)
        pdf.set_text_color(*theme["muted"])
        pdf.cell(0, 6, pdf_text(job["date"]), 0, 1, "R")
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 9.7)
        pdf.set_text_color(*theme["accent_dark"])
        pdf.cell(0, 5, pdf_text(f"{job['company']} | {job['location']}"), ln=1)
        pdf.set_text_color(*theme["text"])
        pdf.set_font("Helvetica", "", 9.6)
        for bullet in job["bullets"]:
            _ensure_space(pdf, 8)
            pdf.set_x(pdf.l_margin + 2)
            pdf.cell(4, 5, "-", 0, 0)
            pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 6, 4.8, pdf_text(bullet))
        pdf.set_y(max(pdf.get_y(), title_y + 14))
        pdf.ln(2)


def _education_block(pdf: StyledPDF, education: list[dict], theme: dict) -> None:
    _section_heading(pdf, "Education", theme)
    for item in education:
        _ensure_space(pdf, 14)
        pdf.set_font("Helvetica", "B", 10.2)
        pdf.set_text_color(*theme["text"])
        pdf.cell(140, 5, pdf_text(item["degree"]), 0, 0)
        pdf.set_font("Helvetica", "", 9.2)
        pdf.set_text_color(*theme["muted"])
        pdf.cell(0, 5, pdf_text(item.get("year", "")), 0, 1, "R")
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 9.6)
        pdf.set_text_color(*theme["accent_dark"])
        pdf.multi_cell(0, 4.8, pdf_text(item["school"]))
        if item.get("details"):
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "", 9.2)
            pdf.set_text_color(*theme["muted"])
            pdf.multi_cell(0, 4.6, pdf_text(item["details"]))
        pdf.ln(1.5)


def _letter_meta(pdf: StyledPDF, items: list[tuple[str, str]], options: dict, theme: dict) -> None:
    if not options.get("show_highlight_strip"):
        return
    _ensure_space(pdf, 18)
    box_gap = 3
    box_width = (PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN - (box_gap * 2)) / 3
    start_y = pdf.get_y()
    for index, (label, value) in enumerate(items):
        x = LEFT_MARGIN + index * (box_width + box_gap)
        pdf.set_fill_color(*theme["panel"])
        pdf.set_draw_color(*theme["line"])
        pdf.rect(x, start_y, box_width, 14, "DF")
        pdf.set_xy(x + 2.5, start_y + 2)
        pdf.set_font("Helvetica", "B", 7.8)
        pdf.set_text_color(*theme["muted"])
        pdf.cell(box_width - 5, 3.8, pdf_text(label.upper()), ln=1)
        pdf.set_x(x + 2.5)
        pdf.set_font("Helvetica", "", 8.8)
        pdf.set_text_color(*theme["text"])
        pdf.multi_cell(box_width - 5, 4.1, pdf_text(value))
    pdf.set_y(start_y + 18)


def _letter_body(
    pdf: StyledPDF,
    recipient: str,
    letter_date: str,
    paragraphs: list[str],
    theme: dict,
) -> None:
    _ensure_space(pdf, 18)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*theme["muted"])
    pdf.cell(0, 5, pdf_text(letter_date), ln=1, align="R")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(*theme["text"])
    pdf.multi_cell(0, 5.6, pdf_text(recipient))
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10.4)
    pdf.set_text_color(*theme["text"])
    for paragraph in paragraphs:
        _ensure_space(pdf, 18)
        pdf.multi_cell(0, 5.7, pdf_text(paragraph))
        pdf.ln(2)


def _document_bytes(pdf: StyledPDF) -> bytes:
    raw = pdf.output(dest="S")
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, bytearray):
        return bytes(raw)
    return str(raw).encode("latin-1", "replace")


def build_cv_pdf_bytes(
    profile: dict,
    config: dict,
    experience: list[dict],
    education: list[dict],
    stats: list[dict],
    contact_line: str,
    options: dict,
    image_path: Path,
) -> bytes:
    pdf = _setup_pdf()
    theme = _theme(options)
    role_line = config.get("role_badge") or config.get("target_role") or "Curriculum Vitae"
    _draw_header(
        pdf,
        profile,
        role_line,
        config.get("tagline", ""),
        contact_line,
        options,
        image_path,
        theme,
    )
    _draw_stats(pdf, stats, options, theme)
    _summary_block(pdf, config.get("summary", ""), theme)
    _skills_block(pdf, list(config.get("skills", [])), theme)
    _experience_block(pdf, experience, theme)
    _education_block(pdf, education, theme)
    return _document_bytes(pdf)


def build_cover_letter_pdf_bytes(
    profile: dict,
    config: dict,
    content: dict,
    contact_line: str,
    letter_date: str,
    options: dict,
    image_path: Path,
) -> bytes:
    pdf = _setup_pdf()
    theme = _theme(options)
    role_line = config.get("target_role") or config.get("role_badge") or "Cover Letter"
    _draw_header(
        pdf,
        profile,
        role_line,
        config.get("tagline", ""),
        contact_line,
        options,
        image_path,
        theme,
    )
    _letter_meta(
        pdf,
        [
            ("Target company", config.get("company_name", "Company")),
            ("Opportunity", config.get("target_role", "Role")),
            ("Focus", content.get("focus", "Tailored application")),
        ],
        options,
        theme,
    )
    _letter_body(
        pdf,
        content.get("recipient", "Dear Hiring Team,"),
        letter_date,
        list(content.get("paragraphs", [])),
        theme,
    )
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10.4)
    pdf.set_text_color(*theme["text"])
    pdf.cell(0, 5.6, pdf_text("Kind regards,"), ln=1)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10.6)
    pdf.cell(0, 5.6, pdf_text(f"{profile['first_name']} {profile['last_name']}"), ln=1)
    return _document_bytes(pdf)
