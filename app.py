"""
MyIPO Document Converter -- single combined Streamlit tool.

Lets you pick the MyIPO notice type from the sidebar, then runs the matching
PDF -> English Word/PDF translator. Each translator's logic lives in its own
module (app_1_change_of_particulars.py, app_2_provisional_refusal.py,
app_3_assignment.py) and is reused here via its render() function, so this
file is just the router/shell.
"""
import subprocess
import streamlit as st

import app_1_change_of_particulars as change_of_particulars
import app_2_provisional_refusal as provisional_refusal
import app_3_assignment as assignment

st.set_page_config(page_title="MyIPO Document Converter", page_icon="📑", layout="centered")


def _git_commit() -> str:
    """Short commit hash of the running code, so a stale Streamlit Cloud
    deploy can be told apart from an actual new bug at a glance."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


TOOLS = {
    "📄 Change of Particulars": change_of_particulars,
    "🚫 Provisional Refusal": provisional_refusal,
    "🔁 Assignment of Trade Mark": assignment,
}

st.sidebar.title("📑 MyIPO Document Converter")
st.sidebar.caption("PDF (Bahasa Malaysia) → English Word / PDF translator")
choice = st.sidebar.radio("Document type", list(TOOLS.keys()))
st.sidebar.markdown("---")
st.sidebar.caption(
    "Each tool auto-extracts and auto-translates fields from the uploaded "
    "PDF, then lets you review/edit before generating the Word or PDF file."
)
st.sidebar.caption(f"Build: {_git_commit()}")

TOOLS[choice].render()
