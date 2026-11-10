# MyIPO Document Converter

A Streamlit tool that converts MyIPO PDF notices (Bahasa Malaysia) into
English Word/PDF translations, matching the house style used in prior
translations (letterhead, field layout, italic disclaimer footer).

## Setup

```
pip install -r requirements.txt
```

## Run

```
streamlit run app.py
```

`app.py` is the single entry point: pick the document type from the sidebar
and the matching translator loads.

| Document type | Notes |
|---|---|
| Change of Particulars | Pertukaran Maklumat Pemohon / Pemilik Cap Dagangan |
| Provisional Refusal | Notis Penolakan Sementara |
| Assignment of Trade Mark | Pindah Milik Cap Dagangan (new template — no prior sample existed) |

Each translator's logic lives in its own module (`app_1_change_of_particulars.py`,
`app_2_provisional_refusal.py`, `app_3_assignment.py`); `app.py` just routes
between them. Those files can still be run standalone too, e.g.
`streamlit run app_2_provisional_refusal.py`, if you only ever need one tool.

## How each tool works

1. Upload the MyIPO PDF.
2. Fields are auto-extracted from the PDF and auto-translated (dates are
   mapped Malay→English; free text is machine-translated via Google
   Translate, which requires internet access; known boilerplate paragraphs
   are substituted with the exact official English wording instead of being
   machine-translated).
3. **Review and edit every field** in the form — this is the most important
   step, since OCR/extraction and machine translation can make mistakes,
   especially for the Provisional Refusal tool's numbered grounds.
4. Click "Generate English Word translation" and download the `.docx` and/or
   `.pdf` (PDF export requires Microsoft Word installed on the machine
   running the app).

## Folder structure

- `sample_documents/` — the original PDFs and their reference Word
  translations, used to design and verify each tool. Not required to run
  the apps; kept for reference.

## Notes

- `common.py` holds the shared PDF-extraction, translation, and Word-styling
  code used by all three tools, so formatting stays consistent across them.
- Tool #2 (Provisional Refusal) recognizes the standard statutory grounds
  (Sections 23(1)(b), 23(1)(c), 23(5)(b), 24(2)(b) of the Trademarks Act
  2019) and fills in the exact official English wording; any ground it
  doesn't recognize falls back to machine translation and should be checked
  carefully before sending.
- Tool #3 (Assignment) has no prior reference translation — its Word layout
  was designed to match the established style of the other two tools.
