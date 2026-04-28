import streamlit as st

st.set_page_config(page_title="NASMI — Identity", page_icon="🪪", layout="wide")

st.title("🪪 Identity Profile")
st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Core Identity")

    col_a, col_b = st.columns(2)
    with col_a:
        st.text_input("Full Name", disabled=True, placeholder="—")
        st.text_input("Date of Birth", disabled=True, placeholder="—")
        st.text_input("Nationality", disabled=True, placeholder="—")
        st.text_input("Place of Birth", disabled=True, placeholder="—")
    with col_b:
        st.text_input("Gender", disabled=True, placeholder="—")
        st.text_input("Mother Tongue", disabled=True, placeholder="—")
        st.text_input("Marital Status", disabled=True, placeholder="—")
        st.text_input("Religion", disabled=True, placeholder="—")

    st.divider()
    st.subheader("Document IDs")
    st.info("No document IDs extracted yet.")

    st.divider()
    st.subheader("Linked Documents")
    st.info("No documents linked yet.")

with col_right:
    st.subheader("Identity Score")
    st.metric("Trust Score", "—")
    st.metric("Completeness", "—")
    st.metric("Verified Fields", "—")

    st.divider()
    st.subheader("Lifecycle State")
    st.selectbox(
        "Current State", ["ACTIVE", "REVIEW", "ARCHIVED", "EXPIRED"], disabled=True
    )

    st.divider()
    st.subheader("Actions")
    st.button("✏️ Edit Profile", disabled=True)
    st.button("🔄 Re-analyze", disabled=True)
    st.button("📤 Export Identity", disabled=True)
