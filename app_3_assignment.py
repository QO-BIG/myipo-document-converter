"""
Streamlit tool #3: Assignment of Registered Trade Mark (PINDAH MILIK CAP DAGANGAN)

No prior English Word translation existed for this MyIPO notice type, so the
output template here was built from scratch to match the house style used in
the Change of Particulars and Provisional Refusal translations (letterhead,
field layout, disclaimer footer) rather than copied from an existing file.
"""
import re
import streamlit as st

import common as c


def parse(text: str) -> dict:
    data = {}

    m = re.search(r"NO\.\s*PENDAFTARAN\s*:\s*([A-Z0-9/]+)", text)
    data["reg_no"] = m.group(1).strip() if m else ""

    m = re.search(r"KELAS\s*:\s*(.+)", text)
    data["class_"] = m.group(1).strip() if m else ""

    m = re.search(r"diterima pada\s+([\d]{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)
    data["received_date"] = c.translate_date(m.group(1)) if m else ""

    m = re.search(r"Nama\s*:\s*(.+?)\n(?:Alamat|$)", text, re.DOTALL)
    data["name"] = m.group(1).strip() if m else ""

    m = re.search(r"Alamat\s*:\s*(.+?)\nTarikh Pindah Milik\s*:", text, re.DOTALL)
    data["address"] = m.group(1).strip() if m else ""

    m = re.search(r"Tarikh Pindah Milik\s*:\s*(\S+)", text)
    data["assignment_date"] = m.group(1).strip() if m else ""

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
    st.title("🔁 Assignment of Trade Mark → English Word Translator")
    st.caption("PINDAH MILIK CAP DAGANGAN")

    uploaded = st.file_uploader("Upload the MyIPO PDF notice", type=["pdf"], key="asn_upload")

    if not uploaded:
        st.info("Upload an Assignment of Trade Mark PDF to begin.")
        return

    pdf_bytes = uploaded.read()
    raw_text = c.extract_pdf_text(pdf_bytes)
    parsed = parse(raw_text)

    with st.expander("Show raw extracted PDF text (for troubleshooting)"):
        st.text(raw_text)

    st.subheader("Review / edit the translated fields before generating the Word file")

    reg_no = st.text_input("Registration No.", parsed["reg_no"], key="asn_reg_no")
    class_ = st.text_input("Class", parsed["class_"], key="asn_class")
    received_date = st.text_input("Date application was received", parsed["received_date"], key="asn_received_date")
    name = st.text_input("Name of new proprietor", parsed["name"], key="asn_name")
    address = st.text_area(
        "Address",
        c.gt_translate(parsed["address"]) if parsed["address"] else "",
        height=100,
        key="asn_address",
    )
    assignment_date = st.text_input("Date of Assignment (dd/mm/yyyy)", parsed["assignment_date"], key="asn_assignment_date")
    letter_date = st.text_input("Letter date", parsed["letter_date"], key="asn_letter_date")
    our_ref = st.text_input("Our Ref", parsed["our_ref"], key="asn_our_ref")
    your_ref = st.text_input("Your Ref", parsed["your_ref"] or "-", key="asn_your_ref")
    to = st.text_area("Addressed To", parsed["to"], height=100, key="asn_to")

    st.caption(
        "Name and address fields are proper nouns and are left as extracted; "
        "edit any line above directly if the auto-translation needs correction."
    )

    if st.button("Generate English Word translation", type="primary", key="asn_generate"):
        doc = c.new_document()
        c.add_translation_tag(doc)
        c.add_header_block(doc)
        c.add_field_block(doc, [("REGISTRATION NO.", reg_no), ("CLASS", class_)], tabs=c.TAB_WIDE)
        c.add_blank(doc)
        c.add_title(doc, "ASSIGNMENT OF REGISTERED TRADE MARK")
        c.add_body(
            doc,
            f"Referring to your application received on {received_date}, the proprietor "
            f"of the trade mark concerned has been recorded as follows:",
        )
        c.add_field_block(
            doc,
            [("Name", name), ("Address", address), ("Date of Assignment", assignment_date)],
            tabs=c.TAB_MID,
        )
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

        out_name = f"{reg_no or 'Assignment'}_English_Translation"
        c.render_download_buttons(st, doc, out_name)


if __name__ == "__main__":
    st.set_page_config(page_title="MyIPO Assignment Translator", page_icon="🔁")
    render()
