import streamlit as st

st.set_page_config(page_title="NASMI — Upload", page_icon="📄", layout="wide")

st.title("📄 Upload + Live Viewer")
st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "docx", "png", "jpg", "tiff"],
        help="Supported: PDF, DOCX, PNG, JPG, TIFF",
    )

    if uploaded_file:
        st.success(f"File uploaded: {uploaded_file.name}")
        st.json(
            {
                "name": uploaded_file.name,
                "size": f"{uploaded_file.size / 1024:.1f} KB",
                "type": uploaded_file.type,
            }
        )

with col_right:
    st.subheader("Live Entity Viewer")
    st.info("Upload a document to see extracted entities.")

    st.subheader("Quality Score Preview")
    st.info("Quality score will appear after processing.")

    st.subheader("Document Lifecycle")
    st.selectbox(
        "Assign Lifecycle State",
        ["UPLOADED", "PROCESSING", "REVIEWED", "ACTIVE", "EXPIRED", "ARCHIVED"],
        disabled=True,
    )
