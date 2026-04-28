import streamlit as st

st.set_page_config(page_title="NASMI — Knowledge Base", page_icon="🧠", layout="wide")

st.title("🧠 Knowledge Base")
st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Extracted Entities")
    entity_type = st.selectbox(
        "Filter by Entity Type",
        [
            "All",
            "PERSON",
            "DATE",
            "LOCATION",
            "ORG",
            "DOCUMENT",
            "ID_NUMBER",
            "ADDRESS",
        ],
    )

    st.info("No entities extracted yet.")

    st.divider()
    st.subheader("Entity Graph")
    st.info("Entity relationship graph will appear here.")

with col_right:
    st.subheader("Summary")
    st.metric("Total Entities", "—")
    st.metric("Unique Names", "—")
    st.metric("Locations", "—")
    st.metric("Dates", "—")

    st.divider()
    st.subheader("Confidence Distribution")
    st.info("Chart will appear after extraction.")

    st.divider()
    st.subheader("Actions")
    st.button("🔄 Re-extract All", disabled=True)
    st.button("🗑️ Clear Knowledge Base", disabled=True)
