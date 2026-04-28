import streamlit as st

st.set_page_config(
    page_title="NASMI — Address & Field Book", page_icon="📒", layout="wide"
)

st.title("📒 Address & Field Book")
st.divider()

tab_address, tab_fields = st.tabs(["📍 Address Book", "🗂️ Field Book"])

with tab_address:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Saved Addresses")
        st.info("No addresses saved yet.")

    with col_right:
        st.subheader("Add Address")
        st.text_input("Label", placeholder="e.g. Home, Work, Embassy...")
        st.text_input("Street")
        st.text_input("City")
        st.text_input("Country")
        st.text_input("Postal Code")
        st.button("💾 Save Address", disabled=True)

with tab_fields:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Custom Fields")
        st.info("No custom fields saved yet.")

    with col_right:
        st.subheader("Add Custom Field")
        st.text_input("Field Name", placeholder="e.g. Tax ID, Social Number...")
        st.text_input("Field Value")
        st.selectbox("Category", ["Personal", "Legal", "Financial", "Medical", "Other"])
        st.button("💾 Save Field", disabled=True)
