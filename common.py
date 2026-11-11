"""
Shared helpers used by all three MyIPO PDF -> English Word translator apps.

Keeps PDF extraction and the document styling (matching the house style used
in the existing sample translations: Times New Roman, [English translation]
header, two-column "Label : Value" fields, and the standard disclaimer
footer) in one place so the three Streamlit tools stay visually and
behaviourally consistent.

The output PDF is built directly with reportlab (no python-docx / LibreOffice
/ Microsoft Word involved) so the app has no system-package dependency and
deploys/starts quickly on Streamlit Community Cloud.
"""
import base64
import io
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

import pdfplumber
import streamlit as st
import streamlit.components.v1 as components

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
# PDF styling (matches the existing sample English-translation documents)
# ---------------------------------------------------------------------------
# reportlab's base-14 fonts include Times-Roman/Bold/Italic, which render as
# Times New Roman in every PDF viewer with no font file to embed/ship.

FONT_NAME = "Times-Roman"
FONT_BOLD = "Times-Bold"
FONT_ITALIC = "Times-Italic"

SIZE_SMALL = 10   # header address block / disclaimer
SIZE_BODY = 11    # field lines / body paragraphs
SIZE_TITLE = 12   # org name / section title

LEFT_MARGIN = 2.5 * cm
RIGHT_MARGIN = 2.5 * cm
TOP_MARGIN = 2.0 * cm
BOTTOM_MARGIN = 2.0 * cm
USABLE_WIDTH = A4[0] - LEFT_MARGIN - RIGHT_MARGIN

# Tab-stop pairs (colon position, value position), carried over from the
# original Word-based layout -- 567 twips == 1cm exactly, which is why these
# convert cleanly. Each field block needs its own matching pair so the
# colons line up vertically the way the reference translations do.
TAB_FOOTER = (1700 / 567 * cm, 2000 / 567 * cm)  # short labels e.g. Our Ref / Your Ref / To
TAB_MID = (2150 / 567 * cm, 2400 / 567 * cm)     # Name/Address, Application No./Class/Applicant...
TAB_WIDE = (7.0 * cm, 7.4 * cm)                  # one long label e.g. APPLICATION / REGISTRATION NO.

NUM_UNIT = 1 * cm  # one outline-numbering indent level (e.g. "2.1")

_BASE_TABLE_STYLE = TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 0),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
])


def _multiline(text: str) -> str:
    """Escape for reportlab's mini-markup and turn embedded newlines into <br/>."""
    lines = (text or "").split("\n")
    return "<br/>".join(_xml_escape(line) for line in lines)


def _para(text, font=FONT_NAME, size=SIZE_BODY, align=TA_LEFT, space_after=0):
    style = ParagraphStyle(
        name="p", fontName=font, fontSize=size, leading=size * 1.15,
        alignment=align, spaceAfter=space_after,
    )
    return Paragraph(_multiline(text), style)


def new_document():
    """A document is just a list of reportlab flowables ("the story")."""
    return []


def add_translation_tag(doc):
    doc.append(_para("[English translation]", font=FONT_ITALIC, size=SIZE_SMALL,
                      align=TA_RIGHT, space_after=10))


def add_header_block(doc):
    """The fixed MyIPO letterhead translation, identical across all document types."""
    lines = [
        ("INTELLECTUAL PROPERTY CORPORATION OF MALAYSIA", FONT_BOLD, SIZE_TITLE, 0),
        ("(Agency under the Ministry of Domestic Trade and Cost of Living)", FONT_NAME, SIZE_SMALL, 0),
        ("Levels LG, G, 2-5, 11-13 & 15-23, Menara MyIPO, PJ Sentral,", FONT_NAME, SIZE_SMALL, 0),
        ("Lot 12, Persiaran Barat, Seksyen 52, 46200 Petaling Jaya, Selangor, MALAYSIA", FONT_NAME, SIZE_SMALL, 0),
        ("Tel: +603 7496 8900   |   Fax: +603 7496 8999   |   www.myipo.gov.my", FONT_NAME, SIZE_SMALL, 6),
    ]
    for text, font, size, space_after in lines:
        doc.append(_para(text, font=font, size=size, space_after=space_after))
    add_blank(doc, space_after=6)
    add_blank(doc, space_after=6)


def add_blank(doc, space_after=8):
    doc.append(Spacer(1, space_after))


def add_title(doc, text: str):
    doc.append(_para(text, font=FONT_BOLD, size=SIZE_TITLE, align=TA_CENTER, space_after=12))


def add_field_block(doc, fields, tabs=TAB_MID, space_after=3):
    """
    Render one or more 'Label : Value' rows sharing the same column widths,
    so the colons and values of adjacent fields line up in a clean column
    (this is what the reference translations do -- fields that belong
    together always share one tab-stop pair).

    `fields` is a list of (label, value) or (label, value, bold_value) tuples.
    Returns the created table.
    """
    label_w = tabs[0]
    colon_w = tabs[1] - tabs[0]
    value_w = USABLE_WIDTH - tabs[1]

    rows = []
    for item in fields:
        label, value = item[0], item[1]
        bold_value = item[2] if len(item) > 2 else True
        rows.append([
            _para(label, font=FONT_BOLD, size=SIZE_BODY),
            _para(":", font=FONT_NAME, size=SIZE_BODY),
            _para(value, font=FONT_BOLD if bold_value else FONT_NAME, size=SIZE_BODY),
        ])

    table = Table(rows, colWidths=[label_w, colon_w, value_w], hAlign="LEFT")
    style = TableStyle(_BASE_TABLE_STYLE.getCommands())
    style.add("BOTTOMPADDING", (0, 0), (-1, -1), space_after)
    table.setStyle(style)
    doc.append(table)
    return table


def add_field(doc, label: str, value: str, bold_value: bool = True, tabs=TAB_MID):
    """Convenience wrapper around add_field_block for a single standalone field."""
    return add_field_block(doc, [(label, value, bold_value)], tabs=tabs)


def add_numbered_para(doc, text: str, justify: bool = True, space_after=11):
    """
    A 'N.\\tBody text' or 'N.N\\tBody text' numbered paragraph, matching the
    outline-numbering indent used in the reference Provisional Refusal
    translation: each nesting level reserves 1cm, and wrapped lines (whether
    from natural word-wrap or an embedded '\\n') fall under the body text
    column rather than snapping back to the margin.
    """
    if "\t" in text:
        number_part, body = text.split("\t", 1)
    else:
        number_part, body = text, ""
    tokens = [t for t in number_part.strip().rstrip(".").split(".") if t]
    depth = max(1, len(tokens))
    indent = depth * NUM_UNIT
    hanging = NUM_UNIT

    combined = f"{number_part}  {body}" if body else number_part
    style = ParagraphStyle(
        name="numbered", fontName=FONT_NAME, fontSize=SIZE_BODY, leading=SIZE_BODY * 1.15,
        alignment=TA_JUSTIFY if justify else TA_LEFT,
        leftIndent=indent, firstLineIndent=-hanging, spaceAfter=space_after,
    )
    doc.append(Paragraph(_multiline(combined), style))


def add_body(doc, text: str, justify: bool = True, space_after=10):
    doc.append(_para(text, align=TA_JUSTIFY if justify else TA_LEFT, space_after=space_after))


def add_signature_block(doc, date_text: str, registrar_line="Registrar of Trade Marks", country_line="Malaysia"):
    left_w = USABLE_WIDTH * 0.55
    right_w = USABLE_WIDTH - left_w
    rows = [
        [_para(f"Date: {date_text}"), _para(registrar_line, font=FONT_BOLD, align=TA_RIGHT)],
        [_para(""), _para(country_line, font=FONT_BOLD, align=TA_RIGHT)],
    ]
    table = Table(rows, colWidths=[left_w, right_w], hAlign="LEFT")
    style = TableStyle(_BASE_TABLE_STYLE.getCommands())
    style.add("BOTTOMPADDING", (0, 1), (-1, 1), 10)
    table.setStyle(style)
    doc.append(table)


def add_disclaimer(doc):
    style = ParagraphStyle(
        name="disclaimer", fontName=FONT_ITALIC, fontSize=SIZE_SMALL, leading=SIZE_SMALL * 1.15,
        alignment=TA_JUSTIFY, spaceBefore=6,
    )
    doc.append(Paragraph(_xml_escape(
        "Translation prepared by Quality Oracle Sdn. Bhd. from the original "
        "document issued in Bahasa Malaysia by the Intellectual Property "
        "Corporation of Malaysia."
    ), style))


def add_table(doc, headers, rows):
    header_style = ParagraphStyle(name="th", fontName=FONT_BOLD, fontSize=SIZE_BODY, leading=SIZE_BODY * 1.15)
    body_style = ParagraphStyle(name="td", fontName=FONT_NAME, fontSize=SIZE_BODY, leading=SIZE_BODY * 1.15)

    data = [[Paragraph(_xml_escape(h), header_style) for h in headers]]
    for row in rows:
        data.append([Paragraph(_multiline(cell), body_style) for cell in row])

    col_w = USABLE_WIDTH / len(headers)
    table = Table(data, colWidths=[col_w] * len(headers), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    doc.append(table)
    doc.append(Spacer(1, 6))
    return table


def build_pdf_bytes(doc) -> bytes:
    buf = io.BytesIO()
    template = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=LEFT_MARGIN, rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN, bottomMargin=BOTTOM_MARGIN,
    )
    template.build(doc)
    return buf.getvalue()


def render_download_buttons(st, doc, base_name: str):
    """
    Build the PDF and trigger the browser download immediately -- no second
    "Download" button to click.

    This renders Streamlit's own st.download_button (whose click-to-download
    mechanism is known to work reliably, since Streamlit handles the Blob URL
    itself), hides it with CSS, and clicks it automatically via a tiny
    injected script. A hand-rolled download link built entirely inside the
    injected script's sandboxed iframe does NOT work reliably -- browsers
    block file downloads originating from inside a sandboxed iframe, which
    is exactly the container st.components.v1.html renders into.
    """
    try:
        with st.spinner("Generating PDF..."):
            pdf_bytes = build_pdf_bytes(doc)
        filename = f"{base_name}.pdf"

        st.markdown(
            "<style>[data-testid='stDownloadButton'] {position: absolute; left: -9999px;}</style>",
            unsafe_allow_html=True,
        )
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            key=f"auto_dl_{base_name}",
        )
        components.html(
            """
            <script>
            setTimeout(function() {
                const doc = window.parent.document;
                const btn = doc.querySelector("[data-testid='stDownloadButton'] button");
                if (btn) { btn.click(); }
            }, 200);
            </script>
            """,
            height=0,
        )
        st.success(f"Downloaded {filename}")
    except Exception as e:
        st.error(f"PDF generation failed: {e}")
