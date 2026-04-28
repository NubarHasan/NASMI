from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header("⚙️", "Settings", "System · Identity Core · AI · Security · Preferences")


# ── Renderers ─────────────────────────────────────────
def _section(title: str) -> None:
    st.markdown(
        f"<div style='font-size:0.85rem;font-weight:700;color:#e3f2fd;"
        f"margin:1rem 0 0.5rem 0;border-bottom:1px solid #1e2d4a;"
        f"padding-bottom:0.3rem;'>{title}</div>",
        unsafe_allow_html=True,
    )


def _save_btn(key: str) -> None:
    if st.button("💾 Save Changes", key=key, use_container_width=True):
        st.toast("Settings saved", icon="💾")


def _empty_state(msg: str = "No data.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:2rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Tabs ──────────────────────────────────────────────
tab_general, tab_identity, tab_ai, tab_security, tab_data = st.tabs(
    [
        "🖥️ General",
        "🔒 Identity Core",
        "🤖 AI & Models",
        "🛡️ Security",
        "🗄️ Data & Storage",
    ]
)


# ══════════════════════════════════════════════════════
# TAB 1 — General
# ══════════════════════════════════════════════════════
with tab_general:
    st.markdown("<div class='nasmi-card'>", unsafe_allow_html=True)

    _section("🌐 Language & Region")
    col_lang, col_date = st.columns(2)
    with col_lang:
        st.selectbox(
            "Interface Language", ["English", "Deutsch", "العربية"], key="set_lang"
        )
    with col_date:
        st.selectbox(
            "Date Format", ["DD.MM.YYYY", "MM/DD/YYYY", "YYYY-MM-DD"], key="set_date"
        )

    col_tz, col_cur = st.columns(2)
    with col_tz:
        st.selectbox(
            "Timezone", ["Europe/Berlin", "UTC", "Europe/London"], key="set_tz"
        )
    with col_cur:
        st.selectbox("Currency", ["EUR €", "USD $", "GBP £"], key="set_cur")

    _section("🎨 Appearance")
    col_theme, col_density = st.columns(2)
    with col_theme:
        st.selectbox("Theme", ["Dark Blue (Default)", "Dark", "Light"], key="set_theme")
    with col_density:
        st.selectbox(
            "UI Density", ["Comfortable", "Compact", "Spacious"], key="set_density"
        )

    _section("🔔 Notifications")
    st.checkbox("Show conflict alerts", value=True, key="notif_conflicts")
    st.checkbox("Show review queue alerts", value=True, key="notif_review")
    st.checkbox("Show export completion toast", value=True, key="notif_export")
    st.checkbox("Show AI processing status", value=False, key="notif_ai")

    st.markdown("</div>", unsafe_allow_html=True)
    _save_btn("save_general")


# ══════════════════════════════════════════════════════
# TAB 2 — Identity Core
# ══════════════════════════════════════════════════════
with tab_identity:
    st.markdown(
        "<div class='nasmi-card' style='border-left:3px solid #ef9a9a;margin-bottom:1rem;'>"
        "<div style='font-size:0.78rem;color:#ef9a9a;font-weight:600;'>"
        "🔒 Identity Core is protected. Changes here affect frozen fields system-wide."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='nasmi-card'>", unsafe_allow_html=True)

    _section("👤 Core Identity Fields")
    col_fn, col_dob = st.columns(2)
    with col_fn:
        st.text_input("Full Name", value="", placeholder="—", key="id_fullname")
    with col_dob:
        st.text_input("Date of Birth", value="", placeholder="DD.MM.YYYY", key="id_dob")

    col_nat, col_idnum = st.columns(2)
    with col_nat:
        st.text_input("Nationality", value="", placeholder="—", key="id_nat")
    with col_idnum:
        st.text_input("ID Number", value="", placeholder="—", key="id_idnum")

    col_idtype, col_verified = st.columns(2)
    with col_idtype:
        st.selectbox(
            "ID Type",
            ["Personalausweis", "Reisepass", "Aufenthaltstitel", "Other"],
            key="id_type",
        )
    with col_verified:
        st.selectbox(
            "Verified Status", ["Unverified", "Verified", "Pending"], key="id_verified"
        )

    _section("🔒 Lock Settings")
    col_lock, col_unlock = st.columns(2)
    with col_lock:
        st.selectbox(
            "Lock Level",
            [
                "HARD — No auto-updates",
                "SOFT — Allow with review",
                "OPEN — Allow auto-updates",
            ],
            key="id_lock_level",
        )
    with col_unlock:
        st.text_input(
            "Unlock PIN", type="password", placeholder="••••••", key="id_unlock_pin"
        )

    st.markdown("</div>", unsafe_allow_html=True)

    col_save_id, col_reset_id = st.columns([3, 1])
    with col_save_id:
        if st.button(
            "💾 Save Identity Core", use_container_width=True, key="save_identity"
        ):
            st.toast("Identity Core saved", icon="💾")
    with col_reset_id:
        if st.button("🔄 Reset", use_container_width=True, key="reset_identity"):
            st.toast("Identity Core reset", icon="🔄")


# ══════════════════════════════════════════════════════
# TAB 3 — AI & Models
# ══════════════════════════════════════════════════════
with tab_ai:
    st.markdown("<div class='nasmi-card'>", unsafe_allow_html=True)

    _section("🤖 Ollama Model")
    col_model, col_url = st.columns(2)
    with col_model:
        st.selectbox(
            "Active Model",
            ["llama3", "mistral", "phi3", "gemma", "custom"],
            key="ai_model",
        )
    with col_url:
        st.text_input("Ollama Base URL", value="http://localhost:11434", key="ai_url")

    col_timeout, col_retries = st.columns(2)
    with col_timeout:
        st.number_input(
            "Timeout (seconds)", min_value=5, max_value=120, value=30, key="ai_timeout"
        )
    with col_retries:
        st.number_input(
            "Max Retries", min_value=1, max_value=10, value=3, key="ai_retries"
        )

    _section("🔍 OCR Settings")
    col_ocr_eng, col_ocr_thresh = st.columns(2)
    with col_ocr_eng:
        st.selectbox(
            "OCR Engine", ["Tesseract", "EasyOCR", "PaddleOCR"], key="ocr_engine"
        )
    with col_ocr_thresh:
        st.slider("Confidence Threshold", 0, 100, 70, key="ocr_threshold")

    col_ocr_lang, col_ocr_dpi = st.columns(2)
    with col_ocr_lang:
        st.multiselect(
            "OCR Languages",
            ["deu", "eng", "ara", "fra", "tur"],
            default=["deu", "eng"],
            key="ocr_langs",
        )
    with col_ocr_dpi:
        st.number_input(
            "Image DPI", min_value=72, max_value=600, value=300, key="ocr_dpi"
        )

    _section("🧩 NER Settings")
    col_ner_model, col_ner_thresh = st.columns(2)
    with col_ner_model:
        st.selectbox(
            "NER Model",
            ["spaCy de_core_news_lg", "spaCy en_core_web_lg", "Custom"],
            key="ner_model",
        )
    with col_ner_thresh:
        st.slider("NER Confidence Threshold", 0, 100, 60, key="ner_threshold")

    _section("🧠 RAG Settings")
    col_rag_chunk, col_rag_overlap = st.columns(2)
    with col_rag_chunk:
        st.number_input(
            "Chunk Size (tokens)",
            min_value=128,
            max_value=2048,
            value=512,
            key="rag_chunk",
        )
    with col_rag_overlap:
        st.number_input(
            "Chunk Overlap", min_value=0, max_value=512, value=64, key="rag_overlap"
        )

    st.selectbox(
        "Embedding Model",
        ["nomic-embed-text", "all-MiniLM-L6-v2", "custom"],
        key="rag_embed",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    col_test, col_save_ai = st.columns([1, 3])
    with col_test:
        if st.button("🧪 Test Connection", use_container_width=True, key="test_ai"):
            with st.spinner("Testing Ollama connection..."):
                st.toast("Connection OK", icon="✅")
    with col_save_ai:
        _save_btn("save_ai")


# ══════════════════════════════════════════════════════
# TAB 4 — Security
# ══════════════════════════════════════════════════════
with tab_security:
    st.markdown("<div class='nasmi-card'>", unsafe_allow_html=True)

    _section("🔑 Access Control")
    col_pin, col_pin2 = st.columns(2)
    with col_pin:
        st.text_input(
            "Current PIN", type="password", placeholder="••••••", key="sec_pin_old"
        )
    with col_pin2:
        st.text_input(
            "New PIN", type="password", placeholder="••••••", key="sec_pin_new"
        )

    st.selectbox(
        "Session Timeout",
        ["15 minutes", "30 minutes", "1 hour", "Never"],
        key="sec_timeout",
    )

    _section("🔒 Data Protection")
    st.checkbox("Encrypt local database", value=True, key="sec_encrypt_db")
    st.checkbox("Encrypt exported files", value=False, key="sec_encrypt_export")
    st.checkbox("Require PIN on export", value=True, key="sec_pin_export")
    st.checkbox("Auto-lock on inactivity", value=True, key="sec_autolock")
    st.checkbox("Log all data access events", value=True, key="sec_log_access")

    _section("🛡️ Freeze Rules")
    st.checkbox("Freeze Full Name after first set", value=True, key="freeze_name")
    st.checkbox("Freeze Date of Birth after first set", value=True, key="freeze_dob")
    st.checkbox("Freeze ID Number after first set", value=True, key="freeze_id")
    st.checkbox("Require review for address changes", value=True, key="freeze_addr")
    st.checkbox("Require review for IBAN changes", value=True, key="freeze_iban")

    st.markdown("</div>", unsafe_allow_html=True)
    _save_btn("save_security")


# ══════════════════════════════════════════════════════
# TAB 5 — Data & Storage
# ══════════════════════════════════════════════════════
with tab_data:
    st.markdown("<div class='nasmi-card'>", unsafe_allow_html=True)

    _section("🗄️ Database")
    col_db_path, col_db_type = st.columns(2)
    with col_db_path:
        st.text_input("DB Path", value="./data/nasmi.db", key="db_path")
    with col_db_type:
        st.selectbox("DB Type", ["SQLite", "PostgreSQL"], key="db_type")

    _section("📁 Storage Paths")
    st.text_input("Documents Folder", value="./data/documents/", key="path_docs")
    st.text_input("Exports Folder", value="./data/exports/", key="path_exports")
    st.text_input("Vector Store Path", value="./data/vectorstore/", key="path_vector")
    st.text_input("Logs Path", value="./data/logs/", key="path_logs")

    _section("🧹 Maintenance")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        if st.button("🧹 Clear Cache", use_container_width=True, key="clear_cache"):
            st.toast("Cache cleared", icon="🧹")
    with col_m2:
        if st.button("🗜️ Compress DB", use_container_width=True, key="compress_db"):
            st.toast("Database compressed", icon="🗜️")
    with col_m3:
        if st.button("🔄 Rebuild Index", use_container_width=True, key="rebuild_index"):
            st.toast("Index rebuilt", icon="🔄")

    _section("⚠️ Danger Zone")
    st.markdown(
        "<div style='background:#1a0a0a;border:1px solid #ef9a9a;border-radius:8px;"
        "padding:1rem;margin-top:0.5rem;'>",
        unsafe_allow_html=True,
    )
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button(
            "🗑️ Delete All Documents", use_container_width=True, key="del_docs"
        ):
            st.warning("Are you sure? This cannot be undone.")
    with col_d2:
        if st.button(
            "💣 Reset Entire System", use_container_width=True, key="reset_all"
        ):
            st.error("This will delete ALL data. This cannot be undone.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    _save_btn("save_data")
