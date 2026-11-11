"""
Streamlit tool #2: Notice of Provisional Refusal (NOTIS PENOLAKAN SEMENTARA)

This notice has a fixed boilerplate shell (paragraphs 1, 3-6, the closing and
signature block are identical on every MyIPO refusal letter) wrapped around a
variable set of numbered grounds (2.1, 2.2, ...) and an optional table of
conflicting trade marks. The grounds are shown exactly as extracted from the
PDF, in the original language.
"""
import re
import streamlit as st

import common as c

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
    data["date"] = m.group(1).strip() if m else ""

    m = re.search(r"bertarikh\s+([\d]{1,2}\s+\w+\s+\d{4})\.", text)
    data["app_date"] = m.group(1).strip() if m else ""

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


def render():
    st.title("🚫 Provisional Refusal \u2192 English Word Translator")
    st.caption("NOTIS PENOLAKAN SEMENTARA")

    uploaded = st.file_uploader("Upload the MyIPO PDF notice", type=["pdf"], key="pr_upload")

    if not uploaded:
        st.info("Upload a Provisional Refusal PDF to begin.")
        return

    pdf_bytes = uploaded.read()
    raw_text = c.extract_pdf_text(pdf_bytes)
    table_rows = c.extract_pdf_tables(pdf_bytes)
    parsed = parse(raw_text)

    with st.expander("Show raw extracted PDF text (for troubleshooting)"):
        st.text(raw_text)

    app_no = parsed["app_no"]
    class_ = parsed["class_"]
    applicant = parsed["applicant"]
    your_ref = parsed["your_ref"]
    date = parsed["date"]
    app_date = parsed["app_date"]
    ground_edits = list(parsed["grounds_raw"])

    default_rows = []
    header_seen = False
    for row in table_rows:
        if not header_seen and row and "permohonan" in (row[0] or "").lower():
            header_seen = True
            continue
        if row and any(row):
            app_num = (row[0] or "").strip()
            status = (row[-1] or "").replace("\n", " ").strip()
            default_rows.append((app_num, status))

    table_text = "\n".join(f"{a} | {s}" for a, s in default_rows)

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

        parsed_rows = []
        for line in table_text.splitlines():
            if "|" in line:
                a, s = line.split("|", 1)
                a, s = a.strip(), s.strip()
                if a or s:
                    parsed_rows.append((a, s))
        if parsed_rows:
            c.add_table(doc, ["Application No.", "Trade Mark", "Status"],
                        [(a, "", s) for a, s in parsed_rows])
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
