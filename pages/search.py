import streamlit as st

st.set_page_config(page_title="NASMI — Search & Query", page_icon="🔍", layout="wide")

st.title("🔍 Search & Query")
st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Natural Language Query")
    query = st.text_input(
        "Ask anything about your documents...",
        placeholder="e.g. What is my passport expiry date?",
    )

    search_mode = st.radio(
        "Search Mode",
        ["Semantic Search", "Exact Match", "AI Query (Ollama)"],
        horizontal=True,
    )

    st.button("🔍 Search", disabled=True)

    st.divider()
    st.subheader("Results")
    st.info("Results will appear here after search.")

with col_right:
    st.subheader("Filters")
    st.multiselect(
        "Document Type",
        ["Passport", "ID Card", "Visa", "Certificate", "Contract", "Other"],
    )
    st.multiselect("Lifecycle State", ["ACTIVE", "EXPIRED", "ARCHIVED", "REVIEW"])
    st.date_input("Date Range — From")
    st.date_input("Date Range — To")
    st.slider("Min Confidence Score", 0, 100, 50)

    st.divider()
    st.subheader("Recent Queries")
    st.info("No recent queries yet.")
