from __future__ import annotations
import tempfile
import streamlit as st
from pathlib import Path

from ui.style import apply_theme, page_header, badge
from core.pipeline import Pipeline, PipelineResult
from intelligence.document_classifier import DocumentIntent
from intelligence.ner_engine import ExtractedEntities
from intelligence.field_schema import DocumentType
from db.database import Database
from db.models import DocumentModel, SystemLogModel
from core.document_loader import DocumentLoader

apply_theme()
page_header(
    "📄",
    "Upload Document",
    "Upload and process documents — OCR · NER · Knowledge Extraction",
)

for _k, _v in [
    ("pipeline_result", None),
    ("pipeline_done", False),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

_doc_model = DocumentModel()
_log_model = SystemLogModel()
_pipeline = Pipeline()


# ── Intent Badge ───────────────────────────────────────────────────────────

INTENT_CONFIG = {
    DocumentIntent.EXTRACT: ("🔍 Extract", "active"),
    DocumentIntent.FILL: ("📝 Fill Form", "new"),
    DocumentIntent.MIXED: ("🔀 Mixed", "pending"),
    DocumentIntent.UNKNOWN: ("❓ Unknown", "expired"),
}


# ── Save to DB ─────────────────────────────────────────────────────────────


def _save_to_db(result: PipelineResult, loaded) -> tuple[int | None, str]:
    try:
        with Database() as db:
            existing = _doc_model.get_by_hash(db, loaded.file_hash)
            if existing:
                return int(existing["id"]), "duplicate"

            doc_id = _doc_model.insert(
                db,
                filename=loaded.filename,
                file_type=loaded.file_type,
                file_size=loaded.file_size,
                file_hash=loaded.file_hash,
            )
            if doc_id is None:
                return None, "error"

            _doc_model.update_status(db, int(doc_id), result.status)

            if result.intent != DocumentIntent.FILL:
                from db.models import EntityModel

                ent_model = EntityModel()
                for f, v in result.extracted_fields.items():
                    if v and f not in ("confidence", "raw_response", "extra"):
                        ent_model.insert(
                            db,
                            document_id=int(doc_id),
                            entity_type=f,
                            entity_value=str(v),
                            confidence=result.quality_score,
                            source=result.doc_type.value,
                        )

            _log_model.log(
                db,
                "INFO",
                "upload",
                f"Document {loaded.filename} processed — intent: {result.intent.value}",
            )
            return int(doc_id), "saved"
    except Exception as e:
        return None, str(e)


# ── Run Pipeline ───────────────────────────────────────────────────────────


def _run(uploaded_file) -> tuple[PipelineResult | None, int | None, str | None]:
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=Path(uploaded_file.name).suffix,
    ) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        loader = DocumentLoader()
        loaded = loader.load(tmp_path)

        result = _pipeline.run(
            file_path=str(tmp_path),
            document_id=loaded.file_hash,
        )

        doc_id, db_status = _save_to_db(result, loaded)
        return result, doc_id, db_status

    except Exception as e:
        return None, None, str(e)
    finally:
        tmp_path.unlink(missing_ok=True)


# ── UI Helpers ─────────────────────────────────────────────────────────────


def _step_row(label: str, status: str, note: str | None = None) -> None:
    STATUS_MAP = {
        "done": "active",
        "skipped": "pending",
        "error": "expired",
        "warn": "new",
    }
    note_html = (
        f"<span style='font-size:0.72rem;color:#546e7a;margin-left:0.5rem;'>{note}</span>"
        if note
        else ""
    )
    st.markdown(
        f"<div class='nasmi-card' style='display:flex;align-items:center;"
        f"gap:0.8rem;padding:0.6rem 1rem;'>"
        f"<span style='font-size:0.85rem;color:#90a4ae;'>{label}</span>"
        f"{note_html}"
        f"<span style='margin-left:auto;'>{badge(status, STATUS_MAP.get(status, 'pending'))}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _metric_card(title: str, value: str, color: str) -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;'>"
        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:1px;'>{title}</div>"
        f"<div style='font-size:1.4rem;font-weight:700;color:{color};"
        f"margin-top:0.4rem;'>{value}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Layout ─────────────────────────────────────────────────────────────────

col_upload, col_preview = st.columns([1, 1])

with col_upload:
    st.markdown("#### 📁 Select Document")

    uploaded_file = st.file_uploader(
        "Drop your file here",
        type=["pdf", "docx", "png", "jpg", "heic", "jpeg", "tiff"],
        help="Supported: PDF, DOCX, PNG, JPG, HEIC, TIFF",
        label_visibility="collapsed",
    )

    if uploaded_file:
        ext = uploaded_file.name.split(".")[-1].upper()
        size_kb = uploaded_file.size / 1024

        st.markdown(
            f"<div class='nasmi-card'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div>"
            f"<div style='font-weight:600;color:#e3f2fd;'>{uploaded_file.name}</div>"
            f"<div style='font-size:0.75rem;color:#546e7a;margin-top:0.2rem;'>"
            f"{size_kb:.1f} KB · {uploaded_file.type}"
            f"</div></div>"
            f"{badge(ext, 'new')}"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        st.divider()

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            process_btn = st.button("🚀 Process Document", use_container_width=True)
        with col_btn2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.pipeline_result = None
                st.session_state.pipeline_done = False
                st.rerun()

        if process_btn:
            st.session_state.pipeline_done = False
            st.session_state.pipeline_result = None

            with st.spinner("Running pipeline..."):
                result, doc_id, db_status = _run(uploaded_file)

            st.session_state.pipeline_result = (result, doc_id, db_status)
            st.session_state.pipeline_done = True
            st.rerun()

        # ── Pipeline Result ──────────────────────────────────────────────
        if st.session_state.pipeline_done and st.session_state.pipeline_result:
            result, doc_id, db_status = st.session_state.pipeline_result

            if result is None:
                st.error(f"Pipeline failed: {db_status}")
            else:
                st.divider()
                st.markdown("#### 🔄 Pipeline Steps")

                intent_label, intent_badge = INTENT_CONFIG[result.intent]

                _step_row("📥 Load Document", "done")
                _step_row(
                    "🔍 OCR / Text Extract",
                    "done" if not result.errors else "warn",
                    f"{len(result.errors)} warning(s)" if result.errors else None,
                )
                _step_row(
                    "🏷️ Classify + Intent",
                    "done",
                    f"{result.doc_type.value} · {intent_label} · {result.confidence:.0%}",
                )
                _step_row(
                    "🧠 NER Extraction",
                    "skipped" if result.intent == DocumentIntent.FILL else "done",
                    f"quality: {result.quality_score:.0%}",
                )
                _step_row(
                    "📝 Form Detection",
                    "done" if result.form_fields else "skipped",
                    f"{len(result.form_fields)} fields" if result.form_fields else None,
                )
                _step_row(
                    "⚠️ Conflicts",
                    "warn" if result.conflicts else "done",
                    f"{len(result.conflicts)} found" if result.conflicts else "None",
                )
                _step_row(
                    "💾 Save to DB",
                    (
                        "skipped"
                        if db_status == "duplicate"
                        else "error" if db_status == "error" else "done"
                    ),
                    db_status if db_status != "saved" else f"ID: {doc_id}",
                )

                st.divider()
                st.markdown("#### 📊 Summary")

                m1, m2, m3 = st.columns(3)
                with m1:
                    _metric_card(
                        "Document Type",
                        result.doc_type.value.replace("_", " ").title(),
                        "#4fc3f7",
                    )
                with m2:
                    color = "#ef9a9a" if result.missing_required else "#a5d6a7"
                    _metric_card(
                        "Missing Required", str(len(result.missing_required)), color
                    )
                with m3:
                    conf_color = (
                        "#a5d6a7"
                        if result.quality_score >= 0.8
                        else "#ffcc80" if result.quality_score >= 0.5 else "#ef9a9a"
                    )
                    _metric_card(
                        "NER Confidence", f"{result.quality_score:.0%}", conf_color
                    )

                if result.missing_required:
                    st.markdown(
                        "<div style='font-size:0.78rem;color:#ef9a9a;"
                        "margin-top:0.8rem;margin-bottom:0.3rem;'>⚠️ Missing required fields:</div>",
                        unsafe_allow_html=True,
                    )
                    for mf in result.missing_required:
                        st.markdown(
                            f"<div class='nasmi-card' style='padding:0.4rem 1rem;"
                            f"font-size:0.82rem;color:#ffcc80;'>· {mf.replace('_', ' ')}</div>",
                            unsafe_allow_html=True,
                        )

                if result.intent == DocumentIntent.FILL and result.form_fields:
                    st.divider()
                    st.markdown("#### 📝 Form Fields Detected")
                    for field in result.form_fields:
                        label = field.get("label", "—")
                        ftype = field.get("type", "text")
                        st.markdown(
                            f"<div class='nasmi-card' style='display:flex;"
                            f"justify-content:space-between;padding:0.4rem 1rem;"
                            f"font-size:0.82rem;'>"
                            f"<span style='color:#e3f2fd;'>{label}</span>"
                            f"<span style='color:#546e7a;'>{ftype}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                if result.errors:
                    with st.expander("⚠️ Pipeline Warnings"):
                        for err in result.errors:
                            st.caption(f"· {err}")

    else:
        st.markdown(
            "<div class='nasmi-card' style='text-align:center;padding:3rem 1rem;"
            "color:#37474f;border:2px dashed #1e2d4a;'>"
            "<div style='font-size:2.5rem;'>📂</div>"
            "<div style='margin-top:0.5rem;font-size:0.9rem;'>No file selected</div>"
            "<div style='font-size:0.75rem;margin-top:0.3rem;'>"
            "PDF · DOCX · PNG · JPG · TIFF</div>"
            "</div>",
            unsafe_allow_html=True,
        )

# ── Preview Column ──────────────────────────────────────────────────────────

with col_preview:
    st.markdown("#### 👁️ Live Preview")

    if uploaded_file:
        ext_lower = uploaded_file.name.split(".")[-1].lower()

        if ext_lower in ["png", "jpg", "jpeg", "tiff"]:
            st.image(uploaded_file, use_container_width=True)
        elif ext_lower == "pdf":
            st.markdown(
                "<div class='nasmi-card' style='text-align:center;padding:2rem;color:#546e7a;'>"
                "<div style='font-size:2rem;'>📄</div>"
                "<div style='margin-top:0.5rem;'>PDF Preview</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='nasmi-card' style='text-align:center;padding:2rem;color:#546e7a;'>"
                "Preview not available for this file type.</div>",
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("#### 🧠 Extracted Entities")

        res_data = st.session_state.pipeline_result
        if res_data:
            result, _, _ = res_data
            if result and result.extracted_fields:
                for f, v in result.extracted_fields.items():
                    if v and f not in ("confidence", "raw_response", "extra"):
                        st.markdown(
                            f"<div class='nasmi-card' style='display:flex;"
                            f"justify-content:space-between;align-items:center;"
                            f"padding:0.5rem 1rem;'>"
                            f"<span style='font-size:0.78rem;color:#546e7a;"
                            f"text-transform:uppercase;letter-spacing:0.5px;'>"
                            f"{f.replace('_', ' ')}</span>"
                            f"<span style='font-size:0.85rem;color:#e3f2fd;"
                            f"font-weight:500;'>{v}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
            else:
                st.markdown(
                    "<div class='nasmi-card' style='color:#37474f;text-align:center;"
                    "padding:1.5rem;font-size:0.85rem;'>"
                    "Entities will appear here after processing.</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("#### 📈 Confidence")
        if res_data:
            result, _, _ = res_data
            if result and result.quality_score > 0:
                conf = result.quality_score
                color = (
                    "#a5d6a7"
                    if conf >= 0.8
                    else "#ffcc80" if conf >= 0.5 else "#ef9a9a"
                )
                st.markdown(
                    f"<div class='nasmi-card' style='text-align:center;padding:1rem;'>"
                    f"<div style='font-size:2rem;font-weight:700;color:{color};'>{conf:.0%}</div>"
                    f"<div style='font-size:0.75rem;color:#546e7a;margin-top:0.3rem;'>"
                    f"Overall NER Confidence</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    else:
        st.markdown(
            "<div class='nasmi-card' style='text-align:center;padding:4rem 1rem;"
            "color:#37474f;border:2px dashed #1e2d4a;'>"
            "<div style='font-size:2.5rem;'>👁️</div>"
            "<div style='margin-top:0.5rem;font-size:0.9rem;'>Preview Area</div>"
            "<div style='font-size:0.75rem;margin-top:0.3rem;'>"
            "Upload a document to see live preview and extracted entities."
            "</div></div>",
            unsafe_allow_html=True,
        )
