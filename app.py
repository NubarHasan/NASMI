import streamlit as st

st.set_page_config(
    page_title="NASMI", page_icon="🧠", layout="wide", initial_sidebar_state="expanded"
)

pages = {
    "🏠 Dashboard": "pages/dashboard.py",
    "📄 Upload": "pages/upload.py",
    "📝 Smart Form Filler": "pages/form_filler.py",
    "🔍 Search & Query": "pages/search.py",
    "🧠 Knowledge Base": "pages/knowledge_base.py",
    "📒 Address & Field Book": "pages/address_field_book.py",
    "📅 Timeline": "pages/timeline.py",
    "⚠️ Contradictions": "pages/contradictions.py",
    "✋ Review Queue": "pages/review_queue.py",
    "🔄 Update Center": "pages/update_center.py",
    "🔐 Identity & Claims": "pages/identity.py",
    "⚙️ Settings": "pages/settings.py",
}

with st.sidebar:
    st.title("🧠 NASMI")
    st.caption("Neural Automated Secure Management of Information")
    st.divider()
    selected = st.radio("Navigation", list(pages.keys()), label_visibility="collapsed")

st.switch_page(pages[selected])
