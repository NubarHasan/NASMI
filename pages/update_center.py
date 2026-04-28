import streamlit as st

st.set_page_config(page_title="NASMI — Update Center", page_icon="🔔", layout="wide")

st.title("🔔 Update Center")
st.divider()

col_left, col_right = st.columns([3, 1])

with col_left:
    st.subheader("Pending Updates")
    st.info("No pending updates.")

    st.divider()
    st.subheader("Update History")
    st.info("No updates applied yet.")

with col_right:
    st.subheader("Summary")
    st.metric("Pending", "—")
    st.metric("Applied Today", "—")
    st.metric("Conflicts", "—")

    st.divider()
    st.subheader("Filters")
    st.selectbox("Status", ["All", "Pending", "Applied", "Rejected", "Conflict"])
    st.selectbox("Source", ["All", "OCR", "Ollama", "Manual", "Form"])
    st.button("🔍 Apply Filters", disabled=True)

    st.divider()
    st.subheader("Actions")
    st.button("✅ Apply All", disabled=True)
    st.button("❌ Reject All", disabled=True)
    st.button("🔄 Refresh", disabled=True)
