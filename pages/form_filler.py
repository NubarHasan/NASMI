import tempfile
import base64
from pathlib import Path

import streamlit as st

from ui.style import apply_theme, page_header, badge
from db.database import Database
from db.models import EntityModel, KnowledgeModel
from intelligence.ocr_engine import OCREngine
from intelligence.form_detector import FormDetector, FieldCategory
from llm.ollama_client import OllamaClient
from config import UPLOAD_DIR

apply_theme()
page_header(
    "📝",
    "Smart Form Filler",
    "Fields are detected automatically from your uploaded form using OCR + AI",
)

# ── Session State ─────────────────────────────────────
for _k, _v in [
    ("fill_mode", "Suggest Only"),
    ("uploaded_form", None),
    ("detect_done", False),
    ("form_fields", []),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Save Uploaded File ────────────────────────────────
def _save_upload(uploaded_file) -> Path:
    dest = UPLOAD_DIR / uploaded_file.name
    dest.write_bytes(uploaded_file.getvalue())
    return dest


# ── Ollama Field Analysis ─────────────────────────────
def _ollama_enrich(full_text: str, detected_labels: list[str]) -> dict[str, str]:
    client = OllamaClient()
    if not client.is_available():
        return {}

    known = ", ".join(detected_labels) if detected_labels else "none"
    prompt = (
        f"You are a form analysis assistant.\n"
        f"Given the following document text, extract any form fields and their values.\n"
        f"Already detected fields: {known}\n"
        f"Focus on fields NOT yet detected.\n"
        f'Return ONLY a JSON object like: {{"field_name": "value", ...}}\n'
        f"No explanation. No markdown.\n\n"
        f"Document text:\n{full_text[:3000]}"
    )

    try:
        response = client.generate(prompt=prompt, model=None)
        import json, re

        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {}


# ── Save to Knowledge Base ────────────────────────────
def _save_to_knowledge(fields: list[tuple]) -> None:
    km = KnowledgeModel()
    with Database() as db:
        for label, value, entity_type, _, confidence in fields:
            if value:
                km.upsert(
                    db=db,
                    field=label.lower(),
                    value=str(value),
                    confidence=confidence / 100,
                    source="form_filler",
                )


# ── Save to Entities ──────────────────────────────────
def _save_to_entities(fields: list[tuple], doc_id: int) -> None:
    em = EntityModel()
    with Database() as db:
        for label, value, entity_type, _, confidence in fields:
            if value:
                em.insert(
                    db=db,
                    document_id=doc_id,
                    entity_type=entity_type,
                    entity_value=str(value),
                    confidence=confidence / 100,
                    source="form_filler",
                )


# ── Register Form as Document ─────────────────────────
def _register_document(filename: str, file_type: str, file_size: float) -> int:
    from db.models import DocumentModel
    import hashlib

    file_hash = hashlib.md5(filename.encode()).hexdigest()
    dm = DocumentModel()
    with Database() as db:
        existing = dm.get_by_hash(db, file_hash)
        if existing:
            return int(existing["id"])
        doc_id = dm.insert(
            db=db,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash,
        )
        return int(doc_id)


# ── Main Detection Pipeline ───────────────────────────
def _run_detection(uploaded_file) -> list[tuple[str, str | None, str, str, int]]:
    file_path = _save_upload(uploaded_file)
    file_ext = file_path.suffix.lower().lstrip(".")

    # Step 1: OCR
    ocr = OCREngine()
    ocr_result = ocr.extract(str(file_path))

    if ocr_result["status"] != "success" or not ocr_result["full_text"].strip():
        st.warning("⚠️ Could not extract text from this file.")
        return []

    pages = ocr_result["pages"]
    full_text = ocr_result["full_text"]

    # Step 2: FormDetector (patterns + labels)
    detector = FormDetector()
    detection = detector.detect(document_id=uploaded_file.name, pages=pages)

    detected_labels = [f.label for f in detection.fields]
    results: dict[str, tuple[str, str, int]] = {}

    for f in detection.fields:
        conf = int(f.score * 100)
        status = "active" if conf >= 80 else "pending" if conf >= 50 else "new"
        results[f.label] = (f.value, f.category.value, status, conf)

    # Step 3: Ollama enrichment for missing fields
    with st.spinner("🤖 AI is analyzing remaining fields..."):
        ai_fields = _ollama_enrich(full_text, detected_labels)

    for field_name, field_value in ai_fields.items():
        if field_name not in results and field_value:
            results[field_name] = (field_value, "UNKNOWN", "new", 70)

    # Step 4: Search DB for existing values
    final: list[tuple[str, str | None, str, str, int]] = []
    with Database() as db:
        for label, (value, entity_type, status, conf) in results.items():
            row = db.fetchone(
                """
                SELECT entity_value, confidence FROM entities
                WHERE LOWER(entity_type) = LOWER(?)
                ORDER BY confidence DESC LIMIT 1
                """,
                (entity_type,),
            )
            if row and float(row["confidence"]) > conf / 100:
                value = str(row["entity_value"])
                conf = int(float(row["confidence"]) * 100)
                status = "active" if conf >= 80 else "pending"

            final.append((label.title(), value, entity_type, status, conf))

    # Step 5: Save to Knowledge Base + Entities
    doc_id = _register_document(
        filename=uploaded_file.name,
        file_type=file_ext,
        file_size=len(uploaded_file.getvalue()) / 1024,
    )
    _save_to_entities(final, doc_id)
    _save_to_knowledge(final)

    return final


# ── Layout ───────────────────────────────────────────
col_left, col_right = st.columns([1, 1])
detect_btn = False

with col_left:
    st.markdown("#### ⚙️ Fill Configuration")

    fill_mode = st.radio(
        "Fill Mode",
        ["Suggest Only", "Assisted Fill", "Identity Locked Fill"],
        horizontal=False,
    )

    mode_info = {
        "Suggest Only": ("new", "Shows best match per field — you decide"),
        "Assisted Fill": ("pending", "Auto-fills fields — you can override any value"),
        "Identity Locked Fill": (
            "active",
            "Uses Identity Core only — locked, no override",
        ),
    }
    m_status, m_desc = mode_info[fill_mode]
    st.markdown(
        f"<div class='nasmi-card' style='padding:0.6rem 1rem;'>"
        f"{badge(fill_mode, m_status)}"
        f"<div style='font-size:0.78rem;color:#546e7a;margin-top:0.4rem;'>{m_desc}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown("#### 📂 Upload Form to Fill")
    uploaded_form = st.file_uploader(
        "Upload a form",
        type=["pdf", "png", "jpg", "jpeg", "tiff"],
        label_visibility="collapsed",
    )

    if uploaded_form:
        st.session_state.uploaded_form = uploaded_form
        ext = uploaded_form.name.split(".")[-1].upper()
        st.markdown(
            f"<div class='nasmi-card' style='display:flex;justify-content:space-between;"
            f"align-items:center;padding:0.6rem 1rem;'>"
            f"<span style='color:#e3f2fd;font-size:0.85rem;'>{uploaded_form.name}</span>"
            f"{badge(ext, 'new')}"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        detect_btn = st.button(
            "🔍 Detect Fields",
            use_container_width=True,
            disabled=not uploaded_form,
        )
    with col_btn2:
        st.button(
            "📤 Export Filled Form",
            use_container_width=True,
            disabled=True,
        )

# ── Run Detection ─────────────────────────────────────
if detect_btn and uploaded_form:
    with st.spinner("🔍 Extracting text and detecting fields..."):
        st.session_state.form_fields = _run_detection(uploaded_form)
        st.session_state.fill_mode = fill_mode
        st.session_state.detect_done = True

# ── Right Panel ───────────────────────────────────────
with col_right:
    st.markdown("#### 📋 Detected Fields")

    if not st.session_state.uploaded_form:
        st.markdown(
            "<div class='nasmi-card' style='text-align:center;padding:3rem 1rem;"
            "color:#37474f;border:2px dashed #1e2d4a;'>"
            "<div style='font-size:2rem;'>📋</div>"
            "<div style='margin-top:0.5rem;font-size:0.9rem;'>No form uploaded yet</div>"
            "<div style='font-size:0.75rem;margin-top:0.3rem;'>"
            "Upload a form — NASMI will detect all fillable fields automatically."
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    else:
        fields = st.session_state.form_fields if st.session_state.detect_done else []

        if not fields:
            st.markdown(
                "<div class='nasmi-card' style='text-align:center;padding:2rem;"
                "color:#546e7a;font-size:0.85rem;'>"
                "Click <b>🔍 Detect Fields</b> to analyze your form."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='font-size:0.75rem;color:#546e7a;margin-bottom:0.5rem;'>"
                f"✅ {len(fields)} fields detected — saved to Knowledge Base."
                f"</div>",
                unsafe_allow_html=True,
            )

            current_mode = st.session_state.get("fill_mode", fill_mode)

            for field, value, entity_type, status, confidence in fields:
                filled = value is not None and value != ""
                disp_val = str(value) if filled else ""
                conf_text = (
                    f"{confidence}% confidence" if confidence > 0 else "Not found"
                )
                conf_color = (
                    "#a5d6a7"
                    if confidence >= 80
                    else "#ffcc80" if confidence >= 50 else "#ef9a9a"
                )

                st.markdown(
                    f"<div class='nasmi-card' style='padding:0.8rem 1rem;margin-bottom:0.5rem;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                    f"<span style='font-size:0.8rem;color:#546e7a;text-transform:uppercase;"
                    f"letter-spacing:0.5px;'>{field}</span>"
                    f"<div style='display:flex;gap:0.4rem;align-items:center;'>"
                    f"{badge(entity_type, status)}"
                    f"<span style='font-size:0.7rem;color:{conf_color};'>{conf_text}</span>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if current_mode == "Identity Locked Fill":
                    st.text_input(
                        field,
                        value=disp_val,
                        disabled=True,
                        label_visibility="collapsed",
                        key=f"locked_{field}",
                    )
                elif current_mode == "Assisted Fill":
                    st.text_input(
                        field,
                        value=disp_val,
                        placeholder="Auto-fill from Knowledge Base...",
                        label_visibility="collapsed",
                        key=f"assisted_{field}",
                    )
                else:
                    col_f, col_s = st.columns([3, 1])
                    with col_f:
                        st.text_input(
                            field,
                            value="",
                            placeholder=f'Suggested: {disp_val or "—"}',
                            label_visibility="collapsed",
                            key=f"suggest_{field}",
                        )
                    with col_s:
                        st.button(
                            "✅ Use",
                            key=f"use_{field}",
                            use_container_width=True,
                            disabled=not filled,
                        )

                st.markdown("</div>", unsafe_allow_html=True)

            st.divider()

            filled_count = sum(1 for _, v, *_ in fields if v)
            total_count = len(fields)
            pct = int((filled_count / total_count) * 100) if total_count else 0

            st.markdown(
                f"<div class='nasmi-card' style='display:flex;justify-content:space-between;"
                f"align-items:center;padding:0.8rem 1.2rem;'>"
                f"<span style='color:#546e7a;font-size:0.85rem;'>Fields Filled</span>"
                f"<span style='color:#4fc3f7;font-weight:700;'>{filled_count} / {total_count} ({pct}%)</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
