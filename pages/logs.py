import streamlit as st

st.set_page_config(page_title="NASMI — Logs", page_icon="🪵", layout="wide")

st.title("🪵 System Logs")
st.divider()

col_left, col_right = st.columns([3, 1])

with col_left:
    st.subheader("Log Viewer")
    st.info("No logs available yet.")

    st.divider()
    st.subheader("Log Detail")
    st.info("Select a log entry to view details.")

with col_right:
    st.subheader("Filters")
    st.selectbox("Log Level", ["All", "INFO", "WARNING", "ERROR", "CRITICAL"])
    st.multiselect(
        "Module",
        [
            "OCR Engine",
            "Ollama Client",
            "Document Loader",
            "NER Engine",
            "Database",
            "UI",
        ],
    )
    st.date_input("From")
    st.date_input("To")
    st.button("🔍 Apply Filters", disabled=True)

    st.divider()
    st.subheader("Summary")
    st.metric("Total Logs", "—")
    st.metric("Errors", "—")
    st.metric("Warnings", "—")

    st.divider()
    st.subheader("Actions")
    st.button("🔄 Refresh", disabled=True)
    st.button("📤 Export Logs", disabled=True)
    st.button("🗑️ Clear Logs", disabled=True)
