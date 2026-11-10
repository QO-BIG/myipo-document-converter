"""
Shared helpers used by all three MyIPO PDF -> English Word translator apps.

Keeps PDF extraction, Malay->English translation, and the DOCX styling
(matching the house style used in the existing sample translations:
Times New Roman, [English translation] header, two-column "Label : Value"
fields separated by tabs, and the standard disclaimer footer) in one place
so the three Streamlit tools stay visually and behaviourally consistent.
"""
import io
import os
import re
import json
import platform
import subprocess
import tempfile
import urllib.request
import urllib.parse

from docx import Document
from docx.shared import Pt, Cm, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_LINE_SPACING

import pdfplumber
import streamlit as st

# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------
# Streamlit reruns the whole script on every widget interaction (not just on
# submit), so without caching, editing any single field would re-extract the
# PDF from scratch each time. st.cache_data keys on the file bytes, so a
# rerun with the same upload reuses the prior result instantly.

@st.cache_data(show_spinner=False)
def extract_pdf_text(file_bytes: bytes) -> str:
    """Return all page text concatenated with blank-line separators."""
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


@st.cache_data(show_spinner=False)
def extract_pdf_tables(file_bytes: bytes):
    """Return every table found across all pages as a flat list of row-lists."""
    rows = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                rows.extend(table)
    return rows


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

MONTHS_MS_TO_EN = {
    "januari": "January", "februari": "February", "mac": "March",
    "april": "April", "mei": "May", "jun": "June", "julai": "July",
    "ogos": "August", "september": "September", "oktober": "October",
    "november": "November", "disember": "December",
}

_DATE_RE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b")


def translate_date(date_str: str) -> str:
    """'06 Oktober 2026' -> '6 October 2026' (strips leading zero, maps month)."""
    if not date_str:
        return date_str

    def repl(m):
        day, month, year = m.groups()
        month_en = MONTHS_MS_TO_EN.get(month.lower(), month)
        return f"{int(day)} {month_en} {year}"

    return _DATE_RE.sub(repl, date_str.strip())


_translation_cache = {}


def gt_translate(text: str, source: str = "ms", target: str = "en") -> str:
    """
    Translate text via the public (unofficial) Google Translate endpoint.
    Chunks long text to stay under the GET query-length limit, caches results
    for the lifetime of the process, and degrades gracefully (returns the
    original text prefixed with a warning marker) if the network call fails
    -- the Streamlit UI lets the user fix the field by hand in that case.
    """
    text = text.strip()
    if not text:
        return ""

    key = (source, target, text)
    if key in _translation_cache:
        return _translation_cache[key]

    chunks = _split_for_translation(text)
    translated_chunks = []
    for chunk in chunks:
        try:
            translated_chunks.append(_gt_translate_chunk(chunk, source, target))
        except Exception:
            translated_chunks.append(f"[TRANSLATION FAILED - please translate manually]\n{chunk}")

    result = " ".join(translated_chunks)
    _translation_cache[key] = result
    return result


def _split_for_translation(text: str, limit: int = 1500):
    """Split on sentence boundaries, keeping chunks under `limit` chars."""
    if len(text) <= limit:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > limit and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current.strip())
    return chunks or [text[:limit]]


def _gt_translate_chunk(text: str, source: str, target: str) -> str:
    params = urllib.parse.urlencode({
        "client": "gtx", "sl": source, "tl": target, "dt": "t", "q": text,
    })
    url = "https://translate.googleapis.com/translate_a/single?" + params
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(seg[0] for seg in data[0] if seg[0])


# ---------------------------------------------------------------------------
# DOCX styling (matches the existing sample English-translation documents)
# ---------------------------------------------------------------------------

FONT_NAME = "Times New Roman"
SIZE_SMALL = Pt(10)   # header address block / disclaimer
SIZE_BODY = Pt(11)    # field lines / body paragraphs
SIZE_TITLE = Pt(12)   # org name / section title

# Tab-stop pairs (colon position, value position) lifted directly from the
# reference translations -- Word stores these as round twip values, which is
# why plain default tab stops (every 0.5") looked misaligned/"ugly": each
# field block needs its own matching pair so the colons line up vertically.
TAB_FOOTER = (Twips(1700), Twips(2000))  # short labels e.g. Our Ref / Your Ref / To
TAB_MID = (Twips(2150), Twips(2400))     # Name/Address, Application No./Class/Applicant...
TAB_WIDE = (Twips(3500), Twips(3750))    # one long label e.g. APPLICATION / REGISTRATION NO.


def _style_run(run, size=SIZE_BODY, bold=False, italic=False):
    run.font.name = FONT_NAME
    run.font.size = size
    run.bold = bold
    run.italic = italic
    return run


def _set_tabs(paragraph, tabs):
    if not tabs:
        return
    for position in tabs:
        paragraph.paragraph_format.tab_stops.add_tab_stop(position, WD_TAB_ALIGNMENT.LEFT)
    # Hanging indent at the value column: when a field's value wraps or is
    # broken onto multiple lines (w:br), Word only continues at the tab
    # column if the paragraph's left indent is already there -- a line break
    # alone does not repeat the tab. Matches the reference translations.
    value_pos = tabs[-1]
    paragraph.paragraph_format.left_indent = value_pos
    paragraph.paragraph_format.first_line_indent = -value_pos


def new_document() -> Document:
    doc = Document()

    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    style = doc.styles["Normal"]
    style.font.name = FONT_NAME
    style.font.size = SIZE_BODY
    pf = style.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.15
    return doc


def add_translation_tag(doc: Document):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_after = Pt(10)
    _style_run(p.add_run("[English translation]"), size=SIZE_SMALL, italic=True)


def add_header_block(doc: Document):
    """The fixed MyIPO letterhead translation, identical across all document types."""
    lines = [
        ("INTELLECTUAL PROPERTY CORPORATION OF MALAYSIA", True, SIZE_TITLE, Pt(0)),
        ("(Agency under the Ministry of Domestic Trade and Cost of Living)", False, SIZE_SMALL, Pt(0)),
        ("Levels LG, G, 2-5, 11-13 & 15-23, Menara MyIPO, PJ Sentral,", False, SIZE_SMALL, Pt(0)),
        ("Lot 12, Persiaran Barat, Seksyen 52, 46200 Petaling Jaya, Selangor, MALAYSIA", False, SIZE_SMALL, Pt(0)),
        ("Tel: +603 7496 8900   |   Fax: +603 7496 8999   |   www.myipo.gov.my", False, SIZE_SMALL, Pt(6)),
    ]
    for text, bold, size, space_after in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = space_after
        _style_run(p.add_run(text), size=size, bold=bold)
    add_blank(doc, space_after=Pt(6))
    add_blank(doc, space_after=Pt(6))


def add_blank(doc: Document, space_after=Pt(8)):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = space_after
    return p


def add_title(doc: Document, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    _style_run(p.add_run(text), size=SIZE_TITLE, bold=True)


def add_field_block(doc: Document, fields, tabs=TAB_MID, space_after=Pt(3)):
    """
    Render one or more 'Label\\t:\\tValue' lines sharing the same tab stops,
    so the colons and values of adjacent fields line up in a clean column
    (this is what the reference translations do -- fields that belong
    together always share one tab-stop pair).

    `fields` is a list of (label, value) or (label, value, bold_value) tuples.
    Returns the list of created paragraphs.
    """
    paragraphs = []
    for item in fields:
        label, value = item[0], item[1]
        bold_value = item[2] if len(item) > 2 else True

        p = doc.add_paragraph()
        p.paragraph_format.space_after = space_after
        _set_tabs(p, tabs)
        _style_run(p.add_run(label))
        _style_run(p.add_run("\t:\t"))
        lines = (value or "").split("\n")
        for i, line in enumerate(lines):
            run = p.add_run(line)
            _style_run(run, bold=bold_value)
            if i < len(lines) - 1:
                run.add_break()
        paragraphs.append(p)
    return paragraphs


def add_field(doc: Document, label: str, value: str, bold_value: bool = True, tabs=TAB_MID):
    """Convenience wrapper around add_field_block for a single standalone field."""
    return add_field_block(doc, [(label, value, bold_value)], tabs=tabs)[0]


def add_numbered_para(doc: Document, text: str, justify: bool = True, space_after=Pt(11)):
    """
    A 'N.\\tBody text' or 'N.N\\tBody text' numbered paragraph, matching the
    outline-numbering indent used in the reference Provisional Refusal
    translation: each nesting level reserves 567 twips, and wrapped lines
    (whether from natural word-wrap or an embedded '\\n') fall under the body
    text column rather than snapping back to the margin.
    """
    number_part = text.split("\t", 1)[0] if "\t" in text else text
    tokens = [t for t in number_part.strip().rstrip(".").split(".") if t]
    depth = max(1, len(tokens))
    indent = Twips(depth * 567)
    hanging = Twips(567)

    p = doc.add_paragraph()
    if justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_after = space_after
    pf.tab_stops.add_tab_stop(indent, WD_TAB_ALIGNMENT.LEFT)
    pf.left_indent = indent
    pf.first_line_indent = -hanging
    lines = text.split("\n")
    for i, line in enumerate(lines):
        run = p.add_run(line)
        _style_run(run)
        if i < len(lines) - 1:
            run.add_break()
    return p


def add_body(doc: Document, text: str, justify: bool = True, space_after=Pt(10)):
    p = doc.add_paragraph()
    if justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = space_after
    _style_run(p.add_run(text))
    return p


def add_signature_block(doc: Document, date_text: str, registrar_line="Registrar of Trade Marks", country_line="Malaysia"):
    tabs = (Twips(9075),)  # right-aligned name/country sit at a fixed right-hand tab
    p = doc.add_paragraph()
    p.paragraph_format.tab_stops.add_tab_stop(tabs[0], WD_TAB_ALIGNMENT.RIGHT)
    _style_run(p.add_run(f"Date: {date_text}"))
    _style_run(p.add_run("\t"))
    _style_run(p.add_run(registrar_line), bold=True)

    p2 = doc.add_paragraph()
    p2.paragraph_format.tab_stops.add_tab_stop(tabs[0], WD_TAB_ALIGNMENT.RIGHT)
    p2.paragraph_format.space_after = Pt(10)
    _style_run(p2.add_run("\t"))
    _style_run(p2.add_run(country_line), bold=True)


def add_disclaimer(doc: Document):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(6)
    _style_run(
        p.add_run(
            "Translation prepared by Quality Oracle Sdn. Bhd. from the original "
            "document issued in Bahasa Malaysia by the Intellectual Property "
            "Corporation of Malaysia."
        ),
        size=SIZE_SMALL, italic=True,
    )


def add_table(doc: Document, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for cell, text in zip(table.rows[0].cells, headers):
        p = cell.paragraphs[0]
        _style_run(p.add_run(text), bold=True)
    for row in rows:
        cells = table.add_row().cells
        for cell, text in zip(cells, row):
            p = cell.paragraphs[0]
            _style_run(p.add_run(text or ""))
    return table


def doc_to_bytes(doc: Document) -> bytes:
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def doc_to_pdf_bytes(doc: Document) -> bytes:
    """
    Convert the generated Word document to PDF.

    On Windows with Microsoft Word installed, drives Word via COM automation
    (docx2pdf) to reproduce the exact Word layout/fonts. On Streamlit
    Community Cloud (Linux, no Word), falls back to LibreOffice headless
    (`soffice --convert-to pdf`), which renders .docx very closely to Word
    and needs no GUI. Temp files are written with absolute paths, since
    Word's COM interface does not understand POSIX-style paths from a Git
    Bash / MSYS shell.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        docx_path = os.path.abspath(os.path.join(tmp_dir, "output.docx"))
        pdf_path = os.path.abspath(os.path.join(tmp_dir, "output.pdf"))
        doc.save(docx_path)

        if platform.system() == "Windows":
            import pythoncom
            from docx2pdf import convert

            pythoncom.CoInitialize()
            try:
                convert(docx_path, pdf_path)
            finally:
                pythoncom.CoUninitialize()
        else:
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", tmp_dir,
                    docx_path,
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0 or not os.path.exists(pdf_path):
                raise RuntimeError(
                    "PDF conversion via LibreOffice failed: "
                    f"{result.stderr or result.stdout}"
                )

        with open(pdf_path, "rb") as f:
            return f.read()


def render_download_buttons(st, doc: Document, base_name: str):
    """
    Shared UI: a Word download button plus a PDF download button (converted
    via Microsoft Word on the machine running the app). If PDF conversion
    fails -- e.g. the app is running on a machine without Word installed --
    the Word download still works and a clear error is shown instead of the
    PDF button.
    """
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Download Word (.docx)",
            data=doc_to_bytes(doc),
            file_name=f"{base_name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    with col2:
        try:
            with st.spinner("Converting to PDF via Microsoft Word..."):
                pdf_bytes = doc_to_pdf_bytes(doc)
            st.download_button(
                "⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"{base_name}.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(
                "PDF export failed (requires Microsoft Word installed on this "
                f"machine): {e}"
            )
