import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header(
    "📄",
    "Upload Document",
    "Upload and process documents — OCR · NER · Knowledge Extraction",
)

# ── Layout ───────────────────────────────────────────
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
            f"</div>"
            f"</div>"
            f"{badge(ext, 'new')}"
            f"</div>"
            f"</div>",
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
            ocr_engine = st.selectbox("OCR Engine", ["Auto", "Tesseract", "EasyOCR"])
        with col_b:
            language = st.selectbox("Language", ["Auto", "German", "English", "Arabic"])

        st.toggle("Run NER after OCR", value=True)
        st.toggle("Extract to Knowledge Base", value=True)
        st.toggle("Check for Contradictions", value=True)

        st.divider()

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            process_btn = st.button("🚀 Process Document", use_container_width=True)
        with col_btn2:
            st.button("🗑️ Clear", use_container_width=True)

        # ── Processing Pipeline Status ──
        if process_btn:
            st.divider()
            st.markdown("#### 🔄 Processing Pipeline")

            steps = [
                ("📥 Loading Document", "pending"),
                ("🔍 OCR Extraction", "pending"),
                ("🧠 NER Analysis", "pending"),
                ("🔗 Knowledge Base Merge", "pending"),
                ("⚠️ Contradiction Check", "pending"),
                ("✅ Done", "pending"),
            ]

            for label, status in steps:
                st.markdown(
                    f"<div class='nasmi-card' style='display:flex;align-items:center;"
                    f"gap:0.8rem;padding:0.6rem 1rem;'>"
                    f"<span style='font-size:0.85rem;color:#90a4ae;'>{label}</span>"
                    f"<span style='margin-left:auto;'>{badge('waiting', status)}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.info("Pipeline will be active once processing engine is connected.")

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
                "<div class='nasmi-card' style='text-align:center;padding:2rem;"
                "color:#546e7a;'>"
                "<div style='font-size:2rem;'>📄</div>"
                "<div style='margin-top:0.5rem;'>PDF Preview</div>"
                "<div style='font-size:0.75rem;margin-top:0.3rem;color:#37474f;'>"
                "Full PDF viewer will be active after processing engine is connected."
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='nasmi-card' style='text-align:center;padding:2rem;"
                "color:#546e7a;'>Preview not available for this file type.</div>",
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("#### 🧠 Extracted Entities")
        st.markdown(
            "<div class='nasmi-card' style='color:#37474f;text-align:center;"
            "padding:1.5rem;font-size:0.85rem;'>"
            "Entities will appear here after processing."
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("#### 📊 Confidence Scores")
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
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )
