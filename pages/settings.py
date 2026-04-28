import streamlit as st

st.set_page_config(page_title="NASMI — Settings", page_icon="⚙️", layout="wide")

st.title("⚙️ Settings")
st.divider()

tab_general, tab_ocr, tab_ollama, tab_db = st.tabs(
    ["🔧 General", "📷 OCR", "🤖 Ollama", "🗄️ Database"]
)

with tab_general:
    st.subheader("Application Settings")
    st.text_input("App Name", value="NASMI")
    st.selectbox("Language", ["English", "Arabic", "German", "French"])
    st.selectbox("Theme", ["Light", "Dark", "System"])
    st.toggle("Enable Notifications", value=True)
    st.toggle("Auto-save", value=True)
    st.button("💾 Save General Settings", disabled=True)

with tab_ocr:
    st.subheader("OCR Engine Settings")
    st.selectbox("Primary OCR Engine", ["Tesseract", "EasyOCR", "PaddleOCR"])
    st.selectbox("Fallback OCR Engine", ["None", "Tesseract", "EasyOCR", "PaddleOCR"])
    st.multiselect(
        "Supported Languages",
        ["English", "Arabic", "German", "French", "Kurdish"],
        default=["English"],
    )
    st.slider("Confidence Threshold", 0, 100, 70)
    st.toggle("Enable Preprocessing", value=True)
    st.button("💾 Save OCR Settings", disabled=True)

with tab_ollama:
    st.subheader("Ollama Configuration")
    st.text_input("Ollama Host", value="http://localhost:11434")
    st.text_input("Default Model", value="llama3")
    st.slider("Temperature", 0.0, 1.0, 0.2, step=0.05)
    st.slider("Max Tokens", 256, 4096, 1024, step=256)
    st.toggle("Stream Responses", value=True)
    st.button("🔌 Test Connection", disabled=True)
    st.button("💾 Save Ollama Settings", disabled=True)

with tab_db:
    st.subheader("Database Settings")
    st.text_input("Database Path", value="./data/nasmi.db")
    st.toggle("Auto Backup", value=True)
    st.selectbox("Backup Frequency", ["Daily", "Weekly", "Monthly"])
    st.button("🗄️ Run Backup Now", disabled=True)
    st.button("🗑️ Clear All Data", disabled=True)
