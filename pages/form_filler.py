import streamlit as st

st.set_page_config(
    page_title="NASMI — Smart Form Filler", page_icon="📝", layout="wide"
)

st.title("📝 Smart Form Filler")
st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Select Form Template")
    st.selectbox(
        "Form Type",
        [
            "— Select —",
            "Visa Application",
            "Bank Account",
            "Job Application",
            "Insurance",
            "Custom",
        ],
    )

    st.subheader("Auto-Fill Source")
    st.radio(
        "Fill from",
        ["Knowledge Base", "Specific Document", "Manual Input"],
        horizontal=True,
    )

    st.divider()
    st.subheader("Form Fields")
    st.text_input("Full Name", placeholder="Auto-filled from Knowledge Base...")
    st.text_input("Date of Birth", placeholder="Auto-filled from Knowledge Base...")
    st.text_input("Nationality", placeholder="Auto-filled from Knowledge Base...")
    st.text_input("Address", placeholder="Auto-filled from Knowledge Base...")
    st.text_input("Document Number", placeholder="Auto-filled from Knowledge Base...")

    st.button("⚡ Auto-Fill All Fields", disabled=True)

with col_right:
    st.subheader("Confidence & Source")
    st.info(
        "Field confidence scores and source documents will appear here after auto-fill."
    )

    st.subheader("Conflict Warnings")
    st.warning("No conflicts detected yet.")

    st.subheader("Export")
    st.button("📥 Export as PDF", disabled=True)
    st.button("📋 Copy to Clipboard", disabled=True)
