import tempfile
import streamlit as st
from pathlib import Path
from ui.style import apply_theme, page_header, badge
from core.document_loader import DocumentLoader
from intelligence.ocr_engine import OCREngine
from intelligence.ner_engine import NEREngine
from intelligence.smart_suggest import SmartSuggest
from intelligence.field_schema import DocumentType
from db.database import Database
from db.models import DocumentModel, EntityModel, ContradictionModel, SystemLogModel

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
_ent_model = EntityModel()
_con_model = ContradictionModel()
_log_model = SystemLogModel()
_suggest = SmartSuggest()


def _run_pipeline(
    uploaded_file,
    doc_type: str,
    ocr_engine_choice: str,
    language: str,
    run_ner: bool,
    run_kb: bool,
    run_contradiction: bool,
) -> dict:

    result = {
        "steps": {},
        "entities": None,
        "doc_id": None,
        "error": None,
        "suggestions": None,
    }

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=Path(uploaded_file.name).suffix,
    ) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        # ── Step 1: Load ──
        loader = DocumentLoader()
        loaded = loader.load(tmp_path)
        result["steps"]["📥 Loading Document"] = ("done", None)

        # ── Step 2: OCR ──
        ocr = OCREngine()
        ocr_result = ocr.extract(str(tmp_path))
        if ocr_result.get("error"):
            result["steps"]["🔍 OCR Extraction"] = ("error", ocr_result["error"])
            result["error"] = ocr_result["error"]
            return result
        full_text = ocr_result.get("full_text", "")
        result["steps"]["🔍 OCR Extraction"] = ("done", None)

        # ── Step 3: Save to DB ──
        with Database() as db:
            existing = _doc_model.get_by_hash(db, loaded.file_hash)
            if existing:
                doc_id = int(existing["id"])
                result["steps"]["💾 Save Document"] = (
                    "skipped",
                    "Duplicate — already in DB",
                )
            else:
                new_id = _doc_model.insert(
                    db,
                    filename=loaded.filename,
                    file_type=loaded.file_type,
                    file_size=loaded.file_size,
                    file_hash=loaded.file_hash,
                )
                if new_id is None:
                    raise RuntimeError("Failed to insert document into DB")
                doc_id = int(new_id)
                _doc_model.update_status(db, doc_id, "PROCESSING")
                result["steps"]["💾 Save Document"] = ("done", None)

        result["doc_id"] = doc_id

        # ── Step 4: NER ──
        if run_ner:
            ner = NEREngine()
            entities = ner.extract(full_text)
            result["entities"] = entities
            result["steps"]["🧠 NER Analysis"] = ("done", None)

            if run_kb and entities:
                with Database() as db:
                    for f, v in entities.to_dict().items():
                        if v and f not in ("confidence", "raw_response", "extra"):
                            _ent_model.insert(
                                db,
                                document_id=doc_id,
                                entity_type=f,
                                entity_value=str(v),
                                confidence=entities.confidence,
                                source=doc_type,
                            )
                result["steps"]["🔗 Knowledge Base Merge"] = ("done", None)
            elif run_kb:
                result["steps"]["🔗 Knowledge Base Merge"] = (
                    "skipped",
                    "No entities found",
                )
        else:
            result["steps"]["🧠 NER Analysis"] = ("skipped", "Disabled")
            result["steps"]["🔗 Knowledge Base Merge"] = ("skipped", "NER disabled")

        # ── Step 5: Smart Suggest ──
        if result["entities"]:
            detected_type = (
                DocumentType(doc_type.lower())
                if doc_type != "— Auto Detect —"
                else DocumentType.UNKNOWN
            )
            suggestion = _suggest.analyze(
                fields=result["entities"].to_dict(),
                doc_type=detected_type,
            )
            result["suggestions"] = suggestion
            missing_count = len(suggestion.missing_fields)
            corrections_count = len(suggestion.corrections)
            result["steps"]["💡 Smart Suggestions"] = (
                "done",
                f"{missing_count} missing · {corrections_count} corrections",
            )
        else:
            result["steps"]["💡 Smart Suggestions"] = ("skipped", "No entities")

        # ── Step 6: Contradiction Check ──
        if run_contradiction and result["entities"]:
            with Database() as db:
                existing_entities = _ent_model.get_by_document(db, doc_id)
                conflicts_found = 0
                for ent in existing_entities:
                    same_type = db.fetchall(
                        "SELECT * FROM entities WHERE entity_type = ? AND document_id != ? AND entity_value != ?",
                        (ent["entity_type"], doc_id, ent["entity_value"]),
                    )
                    for conflict in same_type:
                        _con_model.insert(
                            db,
                            field=ent["entity_type"],
                            value_a=ent["entity_value"],
                            value_b=conflict["entity_value"],
                            source_a=str(doc_id),
                            source_b=str(conflict["document_id"]),
                        )
                        conflicts_found += 1
            label = (
                f"{conflicts_found} conflict(s) found"
                if conflicts_found
                else "No conflicts"
            )
            result["steps"]["⚠️ Contradiction Check"] = ("done", label)
        else:
            result["steps"]["⚠️ Contradiction Check"] = ("skipped", "Disabled")

        # ── Step 7: Finalize ──
        with Database() as db:
            _doc_model.update_status(db, doc_id, "REVIEWED")
            _log_model.log(
                db,
                "INFO",
                "upload",
                f"Document {loaded.filename} processed successfully",
            )
        result["steps"]["✅ Done"] = ("done", None)

    except Exception as e:
        result["error"] = str(e)
        result["steps"]["✅ Done"] = ("error", str(e))

    finally:
        tmp_path.unlink(missing_ok=True)

    return result


# ── Layout ────────────────────────────────────────────
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
        st.markdown("#### ⚙️ Processing Options")

        doc_type = st.selectbox(
            "Document Type",
            [
                "— Auto Detect —",
                "Personalausweis",
                "Reisepass",
                "Meldebescheinigung",
                "Lohnabrechnung",
                "Steuerbescheid",
                "Sozialversicherungsausweis",
                "Mietvertrag",
                "Kontoauszug",
                "Other",
            ],
        )

        col_a, col_b = st.columns(2)
        with col_a:
            ocr_engine_choice = st.selectbox(
                "OCR Engine", ["Auto", "Tesseract", "EasyOCR"]
            )
        with col_b:
            language = st.selectbox("Language", ["Auto", "German", "English", "Arabic"])

        run_ner = st.toggle("Run NER after OCR", value=True)
        run_kb = st.toggle("Extract to Knowledge Base", value=True)
        run_contradiction = st.toggle("Check for Contradictions", value=True)

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
                res = _run_pipeline(
                    uploaded_file,
                    doc_type,
                    ocr_engine_choice,
                    language,
                    run_ner,
                    run_kb,
                    run_contradiction,
                )

            st.session_state.pipeline_result = res
            st.session_state.pipeline_done = True
            st.rerun()

        if st.session_state.pipeline_done and st.session_state.pipeline_result:
            res = st.session_state.pipeline_result

            st.divider()
            st.markdown("#### 🔄 Processing Pipeline")

            STATUS_BADGE = {"done": "active", "skipped": "pending", "error": "expired"}

            for label, (status, note) in res["steps"].items():
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
                    f"<span style='margin-left:auto;'>{badge(status, STATUS_BADGE[status])}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # ── Smart Suggestions Panel ──
            suggestion = res.get("suggestions")
            if suggestion:
                st.divider()
                st.markdown("#### 💡 Smart Suggestions")

                s_col1, s_col2, s_col3 = st.columns(3)

                with s_col1:
                    doc_label = (
                        suggestion.suggested_type.value
                        if suggestion.suggested_type
                        else "—"
                    )
                    conf_pct = f"{suggestion.confidence:.0%}"
                    st.markdown(
                        f"<div class='nasmi-card' style='text-align:center;'>"
                        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
                        f"letter-spacing:1px;'>Detected Type</div>"
                        f"<div style='font-size:1.1rem;font-weight:700;color:#4fc3f7;"
                        f"margin-top:0.4rem;'>{doc_label}</div>"
                        f"<div style='font-size:0.75rem;color:#37474f;margin-top:0.2rem;'>"
                        f"confidence {conf_pct}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                with s_col2:
                    missing_count = len(suggestion.missing_fields)
                    color = "#ef9a9a" if missing_count else "#a5d6a7"
                    st.markdown(
                        f"<div class='nasmi-card' style='text-align:center;'>"
                        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
                        f"letter-spacing:1px;'>Missing Fields</div>"
                        f"<div style='font-size:1.6rem;font-weight:700;color:{color};"
                        f"margin-top:0.4rem;'>{missing_count}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                with s_col3:
                    corr_count = len(suggestion.corrections)
                    color = "#ffcc80" if corr_count else "#a5d6a7"
                    st.markdown(
                        f"<div class='nasmi-card' style='text-align:center;'>"
                        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
                        f"letter-spacing:1px;'>Auto Corrections</div>"
                        f"<div style='font-size:1.6rem;font-weight:700;color:{color};"
                        f"margin-top:0.4rem;'>{corr_count}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                if suggestion.missing_fields:
                    st.markdown(
                        "<div style='font-size:0.78rem;color:#ef9a9a;margin-top:0.8rem;"
                        "margin-bottom:0.3rem;'>⚠️ Missing required fields:</div>",
                        unsafe_allow_html=True,
                    )
                    for mf in suggestion.missing_fields:
                        st.markdown(
                            f"<div class='nasmi-card' style='padding:0.4rem 1rem;"
                            f"font-size:0.82rem;color:#ffcc80;'>"
                            f"· {mf.replace('_', ' ')}</div>",
                            unsafe_allow_html=True,
                        )

                if suggestion.corrections:
                    st.markdown(
                        "<div style='font-size:0.78rem;color:#ffcc80;margin-top:0.8rem;"
                        "margin-bottom:0.3rem;'>🔧 Auto corrections applied:</div>",
                        unsafe_allow_html=True,
                    )
                    for field_name, corrected in suggestion.corrections.items():
                        st.markdown(
                            f"<div class='nasmi-card' style='display:flex;"
                            f"justify-content:space-between;padding:0.4rem 1rem;"
                            f"font-size:0.82rem;'>"
                            f"<span style='color:#546e7a;'>{field_name.replace('_', ' ')}</span>"
                            f"<span style='color:#a5d6a7;'>→ {corrected}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            if res.get("error"):
                st.error(f"Pipeline error: {res['error']}")
            elif res.get("doc_id"):
                st.success(f"✅ Document saved — ID: {res['doc_id']}")

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
                "<div style='font-size:0.75rem;margin-top:0.3rem;color:#37474f;'>"
                "Full PDF viewer coming in final phase.</div>"
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

        res = st.session_state.pipeline_result
        if res and res.get("entities"):
            entities = res["entities"]
            for f, v in entities.to_dict().items():
                if v and f not in ("confidence", "raw_response", "extra"):
                    st.markdown(
                        f"<div class='nasmi-card' style='display:flex;justify-content:space-between;"
                        f"align-items:center;padding:0.5rem 1rem;'>"
                        f"<span style='font-size:0.78rem;color:#546e7a;text-transform:uppercase;"
                        f"letter-spacing:0.5px;'>{f.replace('_', ' ')}</span>"
                        f"<span style='font-size:0.85rem;color:#e3f2fd;font-weight:500;'>{v}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                "<div class='nasmi-card' style='color:#37474f;text-align:center;"
                "padding:1.5rem;font-size:0.85rem;'>"
                "Entities will appear here after processing."
                "</div>",
                unsafe_allow_html=True,
            )

        st.markdown("#### 📊 Confidence Scores")
        if res and res.get("entities"):
            conf = res["entities"].confidence
            color = (
                "#a5d6a7" if conf >= 0.8 else "#ffcc80" if conf >= 0.5 else "#ef9a9a"
            )
            st.markdown(
                f"<div class='nasmi-card' style='text-align:center;padding:1rem;'>"
                f"<div style='font-size:2rem;font-weight:700;color:{color};'>{conf:.0%}</div>"
                f"<div style='font-size:0.75rem;color:#546e7a;margin-top:0.3rem;'>Overall NER Confidence</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='nasmi-card' style='color:#37474f;text-align:center;"
                "padding:1.5rem;font-size:0.85rem;'>"
                "Confidence scores will appear here after processing."
                "</div>",
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
