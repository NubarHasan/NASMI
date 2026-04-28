import streamlit as st

st.set_page_config(page_title="NASMI — Dashboard", page_icon="🏠", layout="wide")

st.title("🏠 Dashboard")
st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Trust Score", value="—", delta=None)

with col2:
    st.metric(label="Active Documents", value="—", delta=None)

with col3:
    st.metric(label="Quality Alerts", value="—", delta=None)

with col4:
    st.metric(label="Review Queue", value="—", delta=None)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📄 Document Lifecycle Status")
    st.info("No documents yet.")

with col_right:
    st.subheader("⚠️ Quality Alerts")
    st.info("No alerts yet.")
