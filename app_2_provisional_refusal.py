"""
Streamlit tool #2: Notice of Provisional Refusal (NOTIS PENOLAKAN SEMENTARA)

This notice has a fixed boilerplate shell (paragraphs 1, 3-6, the closing and
signature block are identical on every MyIPO refusal letter) wrapped around a
variable set of numbered grounds (2.1, 2.2, ...) and an optional table of
conflicting trade marks. Known standard grounds are matched against a
boilerplate dictionary so they come out in the exact official wording;
anything that doesn't match is machine-translated. Fields that are personal/
identifying information (applicant name + address, "To" address block,
reference numbers) are left exactly as extracted, not translated.
"""
import re
import streamlit as st

import common as c

# --- Known standard grounds (Malay boilerplate -> official English wording) ---
# Matched after collapsing whitespace, so line-wrap differences don't matter.
GROUND_TEMPLATES = [
    (
        r"Cap Dagangan tidak mempunyai ciri-ciri distingtif\. Oleh itu, ia tidak menepati\s*"
        r"Seksyen 23\(1\)\(b\) Akta Cap Dagangan 2019\.",
        "Your trade mark does not have any distinctive character. Accordingly, it does not "
        "satisfy Section 23(1)(b) of the Trademarks Act 2019.",
    ),
    (
        r"Cap Dagangan terdiri daripada tanda atau petunjuk yang boleh digunakan dalam\s*"
        r"perdagangan, untuk menunjukkan jenis, kualiti, kuantiti, kegunaan spesifik, nilai,\s*"
        r"tempat asal geografi, ciri-ciri lain barang-barang/perkhidmatan atau masa\s*"
        r"pengeluaran barang-barang atau penyampaian perkhidmatan\. Oleh itu, ia tidak\s*"
        r"menepati Seksyen 23\(1\)\(c\) Akta Cap Dagangan 2019\.",
        "Your trade mark consists of signs or indications that may be used in trade to "
        "designate the kind, quality, quantity, intended purpose, value, geographical "
        "origin, other characteristics of the goods/services, or the time of production of "
        "the goods or rendering of the services. Accordingly, it does not satisfy "
        "Section 23(1)(c) of the Trademarks Act 2019.",
    ),
    (
        r"Cap Dagangan tuan hampir serupa dengan suatu cap dagangan terdahulu dan\s*"
        r"hendak didaftarkan bagi barang-barang/perkhidmatan yang hampir serupa\s*"
        r"dengan cap dagangan terdahulu itu\. Oleh itu, ia tidak menepati Seksyen 24\(2\)\(b\),\s*"
        r"Akta Cap Dagangan 2019\. Cap Dagangan tersebut adalah seperti berikut\s*:?",
        "Your trade mark is similar to an earlier trade mark and is to be registered for "
        "goods/services that are similar to those of the earlier trade mark. Accordingly, "
        "it does not satisfy Section 24(2)(b) of the Trademarks Act 2019. The trade marks "
        "concerned are as follows:",
    ),
]

# Deceptive/misleading ground has a case-specific quoted word; handled separately below.
DECEPTIVE_RE = re.compile(
    r"Penggunaan Cap Dagangan memperdayakan atau mengelirukan orang awam\s*"
    r"tentang sifat, kualiti atau tempat asal geografi barang-barang atau perkhidmatan\.\s*"
    r"Oleh itu, ia tidak menepati Seksyen 23\(5\)\(b\), Akta Cap Dagangan 2019\.\s*"
    r"Penjelasan\s*:\s*(.+)",
    re.DOTALL,
)

FIXED_INTRO = "I am directed to refer to your trade mark application dated {app_date}."
FIXED_PARA2_LEAD = (
    "2.\tFollowing a search and examination, your trade mark application has been found "
    "not to comply with the requirements of the Trademarks Act 2019 in the following respects:"
)
FIXED_PARA3 = "3.\tYou may appeal against the objection raised by:"
FIXED_PARA31 = (
    "3.1\tFormally submitting written representations to the Trademarks Registry, "
    "Intellectual Property Corporation of Malaysia, together with evidence of use by way "
    "of Statutory Declaration (if any); OR"
)
FIXED_PARA32 = (
    "3.2\tRequesting an ex-parte hearing. The request for an ex-parte hearing must be made "
    "by filing Form Fee Code TMC1 (RM 150.00)."
)
FIXED_PARA4 = (
    "4.\tThe action stated in paragraph 3 must be taken within two (2) months from the date "
    "of this letter. An application for an extension of time to take action in this matter "
    "is subject to payment of an extension of time application fee (Form Fee Code TMK1: "
    "RM 50.00) and a fee for each month applied for (Form Fee Code TMK3: RM 100.00 per month)."
)
FIXED_PARA5 = (
    "5.\tIf this office does not receive any reply from you after the said period, this "
    "office will consider that you are not interested in proceeding with the application. "
    "The application will be deemed withdrawn and removed from the list of applications "
    "under consideration pursuant to Section 29(6)(a) of the Trademarks Act 2019 and "
    "Regulation 19(3) of the Trademarks Regulations 2019."
)
FIXED_PARA6 = (
    "6.\tThe Trademarks Act 2019, the Trademarks Regulations 2019 and the Trademarks "
    "Guidelines 2019 may be viewed on the website of the Intellectual Property Corporation "
    "of Malaysia (MyIPO) at www.myipo.gov.my."
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse(text: str) -> dict:
    data = {}
    m = re.search(r"NO\.\s*PERMOHONAN\s*:\s*([A-Z0-9/]+)", text)
    data["app_no"] = m.group(1).strip() if m else ""

    m = re.search(r"KELAS\s*:\s*(.+)", text)
    data["class_"] = m.group(1).strip() if m else ""

    m = re.search(r"PEMOHON\s*:\s*(.+?)\nRUJUKAN TUAN", text, re.DOTALL)
    data["applicant"] = m.group(1).strip() if m else ""

    m = re.search(r"RUJUKAN TUAN\s*:\s*(.+)", text)
    data["your_ref"] = m.group(1).strip() if m else ""

    m = re.search(r"TARIKH\s*:\s*([\d]{1,2}\s+\w+\s+\d{4})", text)
    data["date"] = c.translate_date(m.group(1)) if m else ""

    m = re.search(r"bertarikh\s+([\d]{1,2}\s+\w+\s+\d{4})\.", text)
    data["app_date"] = c.translate_date(m.group(1)) if m else ""

    m = re.search(r"dari aspek berikut\s*:\s*(.+?)(?:\n\s*3\.\s*Tuan boleh|No Permohonan Cap Dagangan Status)",
                   text, re.DOTALL)
    grounds_block = m.group(1).strip() if m else ""

    sub_items = re.split(r"\n(?=2\.\d+\s)", grounds_block)
    grounds = []
    for item in sub_items:
        item = item.strip()
        if not item:
            continue
        item = re.sub(r"^2\.\d+\s*", "", item)
        grounds.append(normalize(item))
    data["grounds_raw"] = grounds

    m = re.search(r"Kepada\s*:\s*(.+?)$", text, re.DOTALL)
    data["to"] = m.group(1).strip() if m else ""

    return data


def translate_ground(ground_norm: str):
    for pattern, english in GROUND_TEMPLATES:
        if re.search(pattern, ground_norm):
            return english
    m = DECEPTIVE_RE.search(ground_norm)
    if m:
        explanation_ms = m.group(1).strip()
        explanation_en = c.gt_translate(explanation_ms)
        base = (
            "The use of your trade mark is deceptive or likely to cause confusion to the "
            "public as to the nature, quality or geographical origin of the goods or "
            "services. Accordingly, it does not satisfy Section 23(5)(b) of the Trademarks "
            "Act 2019."
        )
        return f"{base}\nExplanation: {explanation_en}"
    # Unknown ground -> machine translate
    return c.gt_translate(ground_norm)


def render():
    st.title("🚫 Provisional Refusal \u2192 English Word Translator")
    st.caption("NOTIS PENOLAKAN SEMENTARA")

    uploaded = st.file_uploader("Upload the MyIPO PDF notice", type=["pdf"], key="pr_upload")

    if not uploaded:
        st.info("Upload a Provisional Refusal PDF to begin.")
        return

    pdf_bytes = uploaded.read()
    raw_text = c.extract_pdf_text(pdf_bytes)
    parsed = parse(raw_text)
    conflicting_marks = c.extract_conflicting_marks(pdf_bytes)

    with st.expander("Show raw extracted PDF text (for troubleshooting)"):
        st.text(raw_text)

    app_no = parsed["app_no"]
    class_ = parsed["class_"]
    applicant = parsed["applicant"]
    your_ref = parsed["your_ref"]
    date = parsed["date"]
    app_date = parsed["app_date"]
    ground_edits = [translate_ground(g) for g in parsed["grounds_raw"]]
    to = parsed["to"]

    if st.button("Generate PDF", type="primary", key="pr_generate"):
        doc = c.new_document()
        c.add_translation_tag(doc)
        c.add_header_block(doc)
        c.add_title(doc, "NOTICE OF PROVISIONAL REFUSAL")
        c.add_field_block(
            doc,
            [
                ("Application No.", app_no),
                ("Class", class_),
                ("Applicant", applicant),
                ("Your Ref", your_ref, False),
                ("Date", date, False),
            ],
            tabs=c.TAB_MID,
        )
        c.add_blank(doc)
        c.add_body(doc, FIXED_INTRO.format(app_date=app_date))
        c.add_numbered_para(doc, FIXED_PARA2_LEAD)
        for i, ground in enumerate(ground_edits, start=1):
            c.add_numbered_para(doc, f"2.{i}\t{ground}")

        if conflicting_marks:
            c.add_table(
                doc, ["Application No.", "Trade Mark", "Status"],
                [(a, logo or "", s) for a, s, logo in conflicting_marks],
            )
            c.add_blank(doc)

        c.add_numbered_para(doc, FIXED_PARA3)
        c.add_numbered_para(doc, FIXED_PARA31)
        c.add_numbered_para(doc, FIXED_PARA32)
        c.add_numbered_para(doc, FIXED_PARA4)
        c.add_numbered_para(doc, FIXED_PARA5)
        c.add_numbered_para(doc, FIXED_PARA6)
        c.add_body(doc, "Thank you.")
        c.add_body(doc, "\u201cMALAYSIA MADANI\u201d", justify=False)
        c.add_body(doc, "\u201cSERVING THE NATION\u201d", justify=False)
        c.add_body(doc, "Yours faithfully,", justify=False)
        c.add_body(doc, "(MUHAMMAD HELMY ROSMAINI BIN NAZALUDDIN)", justify=False)
        c.add_body(doc, "On behalf of the Registrar of Trade Marks, Malaysia", justify=False)
        c.add_body(doc, "T: 03-7496 3851  |  E: mhelmy@myipo.gov.my", justify=False)
        c.add_blank(doc)
        c.add_field(doc, "To", to, bold_value=False, tabs=c.TAB_FOOTER)
        c.add_blank(doc)
        c.add_disclaimer(doc)

        out_name = f"{app_no or 'ProvisionalRefusal'}_English_Translation"
        c.render_download_buttons(st, doc, out_name)


if __name__ == "__main__":
    st.set_page_config(page_title="MyIPO Provisional Refusal Translator", page_icon="🚫")
    render()
