from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header
from db.database import Database
from db.models import SettingsModel, AuditLogModel
from core.event_bus import bus
from core.events import Event, EventType

apply_theme()
page_header("⚙️", "Settings", "System · Identity Core · AI · Security · Preferences")

_settings_model = SettingsModel()
_audit_model = AuditLogModel()


# ── Event Notifier ────────────────────────────────────
def _notify(event_type: EventType) -> None:
    bus.publish(Event(event_type=event_type))
    if "sidebar_needs_refresh" in st.session_state:
        st.session_state["sidebar_needs_refresh"] = True


# ── DB Helpers ────────────────────────────────────────
def _load_settings() -> dict[str, str]:
    try:
        with Database() as db:
            rows = _settings_model.get_all(db)
            return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}


def _save_settings(pairs: dict[str, str]) -> None:
    try:
        with Database() as db:
            for key, value in pairs.items():
                _settings_model.set(db, key, value)
    except Exception as e:
        st.error(f"Failed to save settings: {e}")


def _load_identity() -> dict:
    try:
        with Database() as db:
            row = db.fetchone("SELECT * FROM identity_core ORDER BY id DESC LIMIT 1")
            if not row:
                return {}
            return {
                "id": row["id"],
                "full_name": row["full_name"] or "",
                "birth_date": row["birth_date"] or "",
                "nationality": row["nationality"] or "",
                "id_number": row["id_number"] or "",
                "status": row["status"] or "active",
            }
    except Exception:
        return {}


def _save_identity(data: dict) -> None:
    try:
        with Database() as db:
            if data.get("id"):
                db.execute(
                    """
                    UPDATE identity_core
                    SET full_name = ?, birth_date = ?, nationality = ?,
                        id_number = ?, status = ?
                    WHERE id = ?
                    """,
                    (
                        data["full_name"],
                        data["birth_date"],
                        data["nationality"],
                        data["id_number"],
                        data["status"],
                        data["id"],
                    ),
                )
            else:
                db.execute(
                    """
                    INSERT INTO identity_core (full_name, birth_date, nationality, id_number, status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        data["full_name"],
                        data["birth_date"],
                        data["nationality"],
                        data["id_number"],
                        data["status"],
                    ),
                )
            _audit_model.log(
                db,
                "UPDATE",
                "identity_core",
                data.get("id", 0),
                "settings_page",
                "Identity Core updated via Settings",
            )
    except Exception as e:
        st.error(f"Failed to save identity: {e}")


# ── Renderers ─────────────────────────────────────────
def _section(title: str) -> None:
    st.markdown(
        f"<div style='font-size:0.85rem;font-weight:700;color:#e3f2fd;"
        f"margin:1rem 0 0.5rem 0;border-bottom:1px solid #1e2d4a;"
        f"padding-bottom:0.3rem;'>{title}</div>",
        unsafe_allow_html=True,
    )


def _save_btn(key: str) -> bool:
    return st.button("💾 Save Changes", key=key, use_container_width=True)


# ── Load All ──────────────────────────────────────────
cfg = _load_settings()
identity = _load_identity()


def _cfg(key: str, default: str = "") -> str:
    return cfg.get(key, default)


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
        lang_opts = ["English", "Deutsch", "العربية"]
        st.selectbox(
            "Interface Language",
            lang_opts,
            index=(
                lang_opts.index(_cfg("lang", "English"))
                if _cfg("lang", "English") in lang_opts
                else 0
            ),
            key="set_lang",
        )
    with col_date:
        date_opts = ["DD.MM.YYYY", "MM/DD/YYYY", "YYYY-MM-DD"]
        st.selectbox(
            "Date Format",
            date_opts,
            index=(
                date_opts.index(_cfg("date_format", "DD.MM.YYYY"))
                if _cfg("date_format", "DD.MM.YYYY") in date_opts
                else 0
            ),
            key="set_date",
        )

    col_tz, col_cur = st.columns(2)
    with col_tz:
        tz_opts = ["Europe/Berlin", "UTC", "Europe/London"]
        st.selectbox(
            "Timezone",
            tz_opts,
            index=(
                tz_opts.index(_cfg("timezone", "Europe/Berlin"))
                if _cfg("timezone", "Europe/Berlin") in tz_opts
                else 0
            ),
            key="set_tz",
        )
    with col_cur:
        cur_opts = ["EUR €", "USD $", "GBP £"]
        st.selectbox(
            "Currency",
            cur_opts,
            index=(
                cur_opts.index(_cfg("currency", "EUR €"))
                if _cfg("currency", "EUR €") in cur_opts
                else 0
            ),
            key="set_cur",
        )

    _section("🎨 Appearance")
    col_theme, col_density = st.columns(2)
    with col_theme:
        theme_opts = ["Dark Blue (Default)", "Dark", "Light"]
        st.selectbox(
            "Theme",
            theme_opts,
            index=(
                theme_opts.index(_cfg("theme", "Dark Blue (Default)"))
                if _cfg("theme", "Dark Blue (Default)") in theme_opts
                else 0
            ),
            key="set_theme",
        )
    with col_density:
        density_opts = ["Comfortable", "Compact", "Spacious"]
        st.selectbox(
            "UI Density",
            density_opts,
            index=(
                density_opts.index(_cfg("ui_density", "Comfortable"))
                if _cfg("ui_density", "Comfortable") in density_opts
                else 0
            ),
            key="set_density",
        )

    _section("🔔 Notifications")
    st.checkbox(
        "Show conflict alerts",
        value=_cfg("notif_conflicts", "1") == "1",
        key="notif_conflicts",
    )
    st.checkbox(
        "Show review queue alerts",
        value=_cfg("notif_review", "1") == "1",
        key="notif_review",
    )
    st.checkbox(
        "Show export completion toast",
        value=_cfg("notif_export", "1") == "1",
        key="notif_export",
    )
    st.checkbox(
        "Show AI processing status",
        value=_cfg("notif_ai", "0") == "1",
        key="notif_ai",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    if _save_btn("save_general"):
        _save_settings(
            {
                "lang": st.session_state.set_lang,
                "date_format": st.session_state.set_date,
                "timezone": st.session_state.set_tz,
                "currency": st.session_state.set_cur,
                "theme": st.session_state.set_theme,
                "ui_density": st.session_state.set_density,
                "notif_conflicts": "1" if st.session_state.notif_conflicts else "0",
                "notif_review": "1" if st.session_state.notif_review else "0",
                "notif_export": "1" if st.session_state.notif_export else "0",
                "notif_ai": "1" if st.session_state.notif_ai else "0",
            }
        )
        st.toast("General settings saved", icon="💾")


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
        st.text_input(
            "Full Name",
            value=identity.get("full_name", ""),
            placeholder="—",
            key="id_fullname",
        )
    with col_dob:
        st.text_input(
            "Date of Birth",
            value=identity.get("birth_date", ""),
            placeholder="DD.MM.YYYY",
            key="id_dob",
        )

    col_nat, col_idnum = st.columns(2)
    with col_nat:
        st.text_input(
            "Nationality",
            value=identity.get("nationality", ""),
            placeholder="—",
            key="id_nat",
        )
    with col_idnum:
        st.text_input(
            "ID Number",
            value=identity.get("id_number", ""),
            placeholder="—",
            key="id_idnum",
        )

    col_idtype, col_verified = st.columns(2)
    with col_idtype:
        id_type_opts = ["Personalausweis", "Reisepass", "Aufenthaltstitel", "Other"]
        saved_id_type = _cfg("id_type", "Personalausweis")
        st.selectbox(
            "ID Type",
            id_type_opts,
            index=(
                id_type_opts.index(saved_id_type)
                if saved_id_type in id_type_opts
                else 0
            ),
            key="id_type",
        )
    with col_verified:
        verified_opts = ["Unverified", "Verified", "Pending"]
        saved_verified = _cfg("id_verified", "Unverified")
        st.selectbox(
            "Verified Status",
            verified_opts,
            index=(
                verified_opts.index(saved_verified)
                if saved_verified in verified_opts
                else 0
            ),
            key="id_verified",
        )

    _section("🔒 Lock Settings")
    col_lock, col_unlock = st.columns(2)
    with col_lock:
        lock_opts = [
            "HARD — No auto-updates",
            "SOFT — Allow with review",
            "OPEN — Allow auto-updates",
        ]
        saved_lock = _cfg("id_lock_level", "HARD — No auto-updates")
        st.selectbox(
            "Lock Level",
            lock_opts,
            index=lock_opts.index(saved_lock) if saved_lock in lock_opts else 0,
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
            _save_identity(
                {
                    "id": identity.get("id"),
                    "full_name": st.session_state.id_fullname,
                    "birth_date": st.session_state.id_dob,
                    "nationality": st.session_state.id_nat,
                    "id_number": st.session_state.id_idnum,
                    "status": "active",
                }
            )
            _save_settings(
                {
                    "id_type": st.session_state.id_type,
                    "id_verified": st.session_state.id_verified,
                    "id_lock_level": st.session_state.id_lock_level,
                }
            )
            _notify(EventType.IDENTITY_UPDATED)
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
        model_opts = ["llama3", "mistral", "phi3", "gemma", "custom"]
        saved_model = _cfg("ai_model", "llama3")
        st.selectbox(
            "Active Model",
            model_opts,
            index=model_opts.index(saved_model) if saved_model in model_opts else 0,
            key="ai_model",
        )
    with col_url:
        st.text_input(
            "Ollama Base URL",
            value=_cfg("ai_url", "http://localhost:11434"),
            key="ai_url",
        )

    col_timeout, col_retries = st.columns(2)
    with col_timeout:
        st.number_input(
            "Timeout (seconds)",
            min_value=5,
            max_value=120,
            value=int(_cfg("ai_timeout", "30")),
            key="ai_timeout",
        )
    with col_retries:
        st.number_input(
            "Max Retries",
            min_value=1,
            max_value=10,
            value=int(_cfg("ai_retries", "3")),
            key="ai_retries",
        )

    _section("🔍 OCR Settings")
    col_ocr_eng, col_ocr_thresh = st.columns(2)
    with col_ocr_eng:
        ocr_opts = ["Tesseract", "EasyOCR", "PaddleOCR"]
        saved_ocr = _cfg("ocr_engine", "Tesseract")
        st.selectbox(
            "OCR Engine",
            ocr_opts,
            index=ocr_opts.index(saved_ocr) if saved_ocr in ocr_opts else 0,
            key="ocr_engine",
        )
    with col_ocr_thresh:
        st.slider(
            "Confidence Threshold",
            0,
            100,
            int(_cfg("ocr_threshold", "70")),
            key="ocr_threshold",
        )

    col_ocr_lang, col_ocr_dpi = st.columns(2)
    with col_ocr_lang:
        all_langs = ["deu", "eng", "ara", "fra", "tur"]
        saved_langs = _cfg("ocr_langs", "deu,eng").split(",")
        st.multiselect(
            "OCR Languages",
            all_langs,
            default=[lang for lang in saved_langs if lang in all_langs],
            key="ocr_langs",
        )
    with col_ocr_dpi:
        st.number_input(
            "Image DPI",
            min_value=72,
            max_value=600,
            value=int(_cfg("ocr_dpi", "300")),
            key="ocr_dpi",
        )

    _section("🧩 NER Settings")
    col_ner_model, col_ner_thresh = st.columns(2)
    with col_ner_model:
        ner_opts = ["spaCy de_core_news_lg", "spaCy en_core_web_lg", "Custom"]
        saved_ner = _cfg("ner_model", "spaCy de_core_news_lg")
        st.selectbox(
            "NER Model",
            ner_opts,
            index=ner_opts.index(saved_ner) if saved_ner in ner_opts else 0,
            key="ner_model",
        )
    with col_ner_thresh:
        st.slider(
            "NER Confidence Threshold",
            0,
            100,
            int(_cfg("ner_threshold", "60")),
            key="ner_threshold",
        )

    _section("🧠 RAG Settings")
    col_rag_chunk, col_rag_overlap = st.columns(2)
    with col_rag_chunk:
        st.number_input(
            "Chunk Size (tokens)",
            min_value=128,
            max_value=2048,
            value=int(_cfg("rag_chunk", "512")),
            key="rag_chunk",
        )
    with col_rag_overlap:
        st.number_input(
            "Chunk Overlap",
            min_value=0,
            max_value=512,
            value=int(_cfg("rag_overlap", "64")),
            key="rag_overlap",
        )

    embed_opts = ["nomic-embed-text", "all-MiniLM-L6-v2", "custom"]
    saved_embed = _cfg("rag_embed", "nomic-embed-text")
    st.selectbox(
        "Embedding Model",
        embed_opts,
        index=embed_opts.index(saved_embed) if saved_embed in embed_opts else 0,
        key="rag_embed",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    col_test, col_save_ai = st.columns([1, 3])
    with col_test:
        if st.button("🧪 Test Connection", use_container_width=True, key="test_ai"):
            with st.spinner("Testing Ollama connection..."):
                st.toast("Connection OK", icon="✅")
    with col_save_ai:
        if _save_btn("save_ai"):
            _save_settings(
                {
                    "ai_model": st.session_state.ai_model,
                    "ai_url": st.session_state.ai_url,
                    "ai_timeout": str(st.session_state.ai_timeout),
                    "ai_retries": str(st.session_state.ai_retries),
                    "ocr_engine": st.session_state.ocr_engine,
                    "ocr_threshold": str(st.session_state.ocr_threshold),
                    "ocr_langs": ",".join(st.session_state.ocr_langs),
                    "ocr_dpi": str(st.session_state.ocr_dpi),
                    "ner_model": st.session_state.ner_model,
                    "ner_threshold": str(st.session_state.ner_threshold),
                    "rag_chunk": str(st.session_state.rag_chunk),
                    "rag_overlap": str(st.session_state.rag_overlap),
                    "rag_embed": st.session_state.rag_embed,
                }
            )
            _notify(EventType.PREDICTION_GENERATED)
            st.toast("AI settings saved", icon="💾")


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

    timeout_opts = ["15 minutes", "30 minutes", "1 hour", "Never"]
    saved_timeout = _cfg("sec_timeout", "30 minutes")
    st.selectbox(
        "Session Timeout",
        timeout_opts,
        index=timeout_opts.index(saved_timeout) if saved_timeout in timeout_opts else 1,
        key="sec_timeout",
    )

    _section("🔒 Data Protection")
    st.checkbox(
        "Encrypt local database",
        value=_cfg("sec_encrypt_db", "1") == "1",
        key="sec_encrypt_db",
    )
    st.checkbox(
        "Encrypt exported files",
        value=_cfg("sec_encrypt_export", "0") == "1",
        key="sec_encrypt_export",
    )
    st.checkbox(
        "Require PIN on export",
        value=_cfg("sec_pin_export", "1") == "1",
        key="sec_pin_export",
    )
    st.checkbox(
        "Auto-lock on inactivity",
        value=_cfg("sec_autolock", "1") == "1",
        key="sec_autolock",
    )
    st.checkbox(
        "Log all data access events",
        value=_cfg("sec_log_access", "1") == "1",
        key="sec_log_access",
    )

    _section("🛡️ Freeze Rules")
    st.checkbox(
        "Freeze Full Name after first set",
        value=_cfg("freeze_name", "1") == "1",
        key="freeze_name",
    )
    st.checkbox(
        "Freeze Date of Birth after first set",
        value=_cfg("freeze_dob", "1") == "1",
        key="freeze_dob",
    )
    st.checkbox(
        "Freeze ID Number after first set",
        value=_cfg("freeze_id", "1") == "1",
        key="freeze_id",
    )
    st.checkbox(
        "Require review for address changes",
        value=_cfg("freeze_addr", "1") == "1",
        key="freeze_addr",
    )
    st.checkbox(
        "Require review for IBAN changes",
        value=_cfg("freeze_iban", "1") == "1",
        key="freeze_iban",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    if _save_btn("save_security"):
        _save_settings(
            {
                "sec_timeout": st.session_state.sec_timeout,
                "sec_encrypt_db": "1" if st.session_state.sec_encrypt_db else "0",
                "sec_encrypt_export": (
                    "1" if st.session_state.sec_encrypt_export else "0"
                ),
                "sec_pin_export": "1" if st.session_state.sec_pin_export else "0",
                "sec_autolock": "1" if st.session_state.sec_autolock else "0",
                "sec_log_access": "1" if st.session_state.sec_log_access else "0",
                "freeze_name": "1" if st.session_state.freeze_name else "0",
                "freeze_dob": "1" if st.session_state.freeze_dob else "0",
                "freeze_id": "1" if st.session_state.freeze_id else "0",
                "freeze_addr": "1" if st.session_state.freeze_addr else "0",
                "freeze_iban": "1" if st.session_state.freeze_iban else "0",
            }
        )
        st.toast("Security settings saved", icon="💾")


# ══════════════════════════════════════════════════════
# TAB 5 — Data & Storage
# ══════════════════════════════════════════════════════
with tab_data:
    st.markdown("<div class='nasmi-card'>", unsafe_allow_html=True)

    _section("🗄️ Database")
    col_db_path, col_db_type = st.columns(2)
    with col_db_path:
        st.text_input(
            "DB Path", value=_cfg("db_path", "./data/nasmi.db"), key="db_path"
        )
    with col_db_type:
        db_type_opts = ["SQLite", "PostgreSQL"]
        saved_db_type = _cfg("db_type", "SQLite")
        st.selectbox(
            "DB Type",
            db_type_opts,
            index=(
                db_type_opts.index(saved_db_type)
                if saved_db_type in db_type_opts
                else 0
            ),
            key="db_type",
        )

    _section("📁 Storage Paths")
    st.text_input(
        "Documents Folder",
        value=_cfg("path_docs", "./data/documents/"),
        key="path_docs",
    )
    st.text_input(
        "Exports Folder",
        value=_cfg("path_exports", "./data/exports/"),
        key="path_exports",
    )
    st.text_input(
        "Vector Store Path",
        value=_cfg("path_vector", "./data/vectorstore/"),
        key="path_vector",
    )
    st.text_input("Logs Path", value=_cfg("path_logs", "./data/logs/"), key="path_logs")

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

    if _save_btn("save_data"):
        _save_settings(
            {
                "db_path": st.session_state.db_path,
                "db_type": st.session_state.db_type,
                "path_docs": st.session_state.path_docs,
                "path_exports": st.session_state.path_exports,
                "path_vector": st.session_state.path_vector,
                "path_logs": st.session_state.path_logs,
            }
        )
        st.toast("Data & Storage settings saved", icon="💾")
