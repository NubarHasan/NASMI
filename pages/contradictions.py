import streamlit as st

st.set_page_config(page_title="NASMI — Contradictions", page_icon="⚠️", layout="wide")

st.title("⚠️ Contradictions")
st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Detected Contradictions")
    st.info("No contradictions detected yet.")

    st.divider()
    st.subheader("Contradiction Detail")
    st.info("Select a contradiction to view details.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Source A")
        st.info("—")
    with col_b:
        st.subheader("Source B")
        st.info("—")

    st.button("✅ Resolve — Accept Source A", disabled=True)
    st.button("✅ Resolve — Accept Source B", disabled=True)
    st.button("✏️ Resolve — Manual Input", disabled=True)

with col_right:
    st.subheader("Summary")
    st.metric("Total Contradictions", "—")
    st.metric("Resolved", "—")
    st.metric("Pending", "—")

    st.divider()
    st.subheader("Filters")
    st.multiselect(
        "Field Type",
        ["Name", "Date of Birth", "Nationality", "Address", "ID Number", "Other"],
    )
    st.selectbox("Status", ["All", "Pending", "Resolved"])
    st.button("🔍 Apply Filters", disabled=True)
