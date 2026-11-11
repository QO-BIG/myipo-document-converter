"""
Streamlit tool #1: Change of Particulars of Applicant/Proprietor
(PERTUKARAN MAKLUMAT PEMOHON / PEMILIK CAP DAGANGAN)

Upload a MyIPO "change of particulars" PDF notice, review the
auto-extracted / auto-translated fields, then download the English Word
translation in the same house style used for prior translations.
"""
import re
import streamlit as st

import common as c


def parse(text: str) -> dict:
    data = {}

    m = re.search(r"NO\.\s*PERMOHONAN\s*/\s*PENDAFTARAN\s*:\s*([A-Z0-9/]+)", text)
    data["app_no"] = m.group(1).strip() if m else ""

    m = re.search(r"diterima pada\s+([\d]{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)
    data["received_date"] = c.translate_date(m.group(1)) if m else ""

    m = re.search(r"NAMA\s*:\s*(.+?)\n(?:ALAMAT|$)", text, re.DOTALL)
    data["name"] = m.group(1).strip() if m else ""

    m = re.search(r"ALAMAT\s*:\s*(.+?)\nTarikh\s*:", text, re.DOTALL)
    data["address"] = m.group(1).strip() if m else ""

    m = re.search(r"\bTarikh\s*:\s*([\d]{1,2}\s+\w+\s+\d{4})", text)
    data["letter_date"] = c.translate_date(m.group(1)) if m else ""

    m = re.search(r"Rujukan Kami\s*:\s*(.+)", text)
    data["our_ref"] = m.group(1).strip() if m else ""

    m = re.search(r"Rujukan Tuan\s*:\s*(.+)", text)
    data["your_ref"] = m.group(1).strip() if m else ""

    m = re.search(r"Kepada\s*:\s*(.+?)\n\(Agensi", text, re.DOTALL)
    data["to"] = m.group(1).strip() if m else ""

    return data


def render():
    st.title("📄 Change of Particulars → English Word Translator")
    st.caption("PERTUKARAN MAKLUMAT PEMOHON / PEMILIK CAP DAGANGAN")

    uploaded = st.file_uploader("Upload the MyIPO PDF notice", type=["pdf"], key="cop_upload")

    if not uploaded:
        st.info("Upload a Change of Particulars PDF to begin.")
        return

    pdf_bytes = uploaded.read()
    raw_text = c.extract_pdf_text(pdf_bytes)
    parsed = parse(raw_text)

    with st.expander("Show raw extracted PDF text (for troubleshooting)"):
        st.text(raw_text)

    app_no = parsed["app_no"]
    received_date = parsed["received_date"]
    name = parsed["name"]
    address = parsed["address"]
    letter_date = parsed["letter_date"]
    our_ref = parsed["our_ref"]
    your_ref = parsed["your_ref"] or "-"
    to = parsed["to"]

    if st.button("Generate PDF", type="primary", key="cop_generate"):
        doc = c.new_document()
        c.add_translation_tag(doc)
        c.add_header_block(doc)
        c.add_field(doc, "APPLICATION / REGISTRATION NO.", app_no, tabs=c.TAB_WIDE)
        c.add_blank(doc)
        c.add_title(doc, "CHANGE OF PARTICULARS OF APPLICANT / PROPRIETOR OF TRADE MARK")
        c.add_body(
            doc,
            f"Referring to your application received on {received_date}, the particulars "
            f"of the applicant / proprietor of the trade mark have been updated as follows:",
        )
        c.add_field_block(doc, [("Name", name), ("Address", address)], tabs=c.TAB_MID)
        c.add_blank(doc)
        c.add_signature_block(doc, letter_date)
        c.add_blank(doc)
        c.add_field_block(
            doc,
            [("Our Ref", our_ref, False), ("Your Ref", your_ref, False), ("To", to, False)],
            tabs=c.TAB_FOOTER,
        )
        c.add_blank(doc)
        c.add_disclaimer(doc)

        out_name = f"{app_no.replace('/', '-') or 'ChangeOfParticulars'}_English_Translation"
        c.render_download_buttons(st, doc, out_name)


if __name__ == "__main__":
    st.set_page_config(page_title="MyIPO Change of Particulars Translator", page_icon="📄")
    render()
