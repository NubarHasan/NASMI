from __future__ import annotations

import hashlib

import streamlit as st

from ui.state import session_manager as sm
from ui.state.page_id import PageId
from ui.state.session_keys import SessionKeys
from ui.viewmodels.document_models import DocumentDetail, DocumentSummary
from ui.viewmodels.documents_vm import DocumentsVM

_CSS = """
<style>
.documents-title {
    color: #38bdf8;
    font-size: 2rem;
    font-weight: 900;
    margin-bottom: 0.2rem;
}
.documents-subtitle {
    color: #94a3b8;
    font-size: 0.9rem;
    margin-bottom: 1rem;
}
.doc-name {
    color: #f8fafc;
    font-weight: 800;
    font-size: 0.95rem;
}
.doc-meta {
    color: #94a3b8;
    font-size: 0.78rem;
}
.detail-box {
    background: #020617;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 1rem;
}
.preview-box {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 1rem;
    color: #cbd5e1;
    white-space: pre-wrap;
    font-size: 0.85rem;
}
</style>
"""


def _navigate(page: PageId) -> None:
    sm.set(SessionKeys.CURRENT_PAGE, page)
    st.rerun()


def _status_icon(status: str) -> str:
    normalized = status.lower()
    return {
        "pending": "🟡",
        "processing": "🔵",
        "processed": "🟢",
        "failed": "🔴",
    }.get(normalized, "⚪")


def _render_header(entity_id: str) -> None:
    st.markdown(
        """
        <div class="documents-title">Documents Intake</div>
        <div class="documents-subtitle">Upload source documents. The system starts with type "other" and detects the document type after OCR.</div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Active entity ID: {entity_id}")


def _render_no_entity() -> None:
    st.warning("No active entity selected.")
    st.markdown("Create or select an entity before uploading documents.")
    if st.button("Go to Profile", type="primary"):
        _navigate(PageId.PROFILE)


def _render_toolbar(vm: DocumentsVM) -> str:
    col_upload, col_language, col_refresh, col_search = st.columns([4, 1.5, 1, 3])

    with col_language:
        language = st.selectbox(
            "Language",
            ["en", "de", "ar", "tr", "fr", "es"],
            label_visibility="collapsed",
            key="documents_language",
        )

    with col_upload:
        uploaded = st.file_uploader(
            "Upload",
            type=["pdf", "png", "jpg", "jpeg", "txt"],
            label_visibility="collapsed",
            key="documents_upload",
        )

    with col_refresh:
        if st.button("↺", help="Refresh", use_container_width=True):
            sm.reset(SessionKeys.SELECTED_DOCUMENT_ID)
            st.rerun()

    with col_search:
        search = st.text_input(
            "Search",
            placeholder="Filter by file name...",
            label_visibility="collapsed",
            key="documents_search",
        )

    if uploaded:
        file_bytes = uploaded.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        last_hash = st.session_state.get("_last_uploaded_hash")

        if file_hash != last_hash:
            st.session_state["_last_uploaded_hash"] = file_hash

            with st.spinner(f"Processing {uploaded.name}..."):
                result = vm.upload_document(
                    file_bytes=file_bytes,
                    file_name=uploaded.name,
                    language=language,
                )

            if result.success:
                sm.set(SessionKeys.SELECTED_DOCUMENT_ID, result.document_id)
                st.success(f"Document uploaded and processed: {uploaded.name}")
                st.rerun()
            else:
                st.error(result.message or "Upload failed.")

    return search


def _render_document_list(
    documents: tuple[DocumentSummary, ...],
    search: str,
) -> None:
    st.subheader("Entity Documents")

    if not documents:
        st.info("No documents uploaded for this entity yet.")
        return

    filtered = tuple(
        doc
        for doc in documents
        if not search or search.lower() in doc.file_name.lower()
    )

    if not filtered:
        st.info("No documents match your search.")
        return

    for doc in filtered:
        selected = sm.get(SessionKeys.SELECTED_DOCUMENT_ID) == doc.document_id

        with st.container(border=True):
            st.markdown(f"**{_status_icon(doc.status)} {doc.file_name}**")
            st.caption(f"{doc.document_type} · {doc.status}")

            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.caption(
                    f"Confidence: {doc.confidence:.0%}"
                    if doc.confidence is not None
                    else "Confidence: —"
                )
            with col_b:
                button_label = "Selected" if selected else "View"
                if st.button(
                    button_label,
                    key=f"view_document_{doc.document_id}",
                    use_container_width=True,
                    disabled=selected,
                ):
                    sm.set(SessionKeys.SELECTED_DOCUMENT_ID, doc.document_id)
                    st.rerun()


def _render_document_detail(detail: DocumentDetail) -> None:
    st.subheader("Document Detail")

    st.markdown(
        f"""
        <div class="detail-box">
            <div class="doc-name">{detail.file_name}</div>
            <div class="doc-meta">ID: {detail.document_id}</div>
            <div class="doc-meta">Detected Type: {detail.document_type}</div>
            <div class="doc-meta">Status: {_status_icon(detail.status)} {detail.status}</div>
            <div class="doc-meta">Created: {detail.created_at}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Pages", detail.page_count)
    with col_b:
        st.metric("Extracted Fields", detail.extracted_fields_count)
    with col_c:
        st.metric("Conflicts", detail.conflict_count)
    with col_d:
        st.metric(
            "Confidence",
            f"{detail.confidence:.0%}" if detail.confidence is not None else "—",
        )

    if detail.review_required:
        st.warning("Review required. Candidate facts are waiting in Review.")

    if detail.status.lower() == "failed":
        st.error("This document failed during processing.")

    if detail.preview_text:
        st.divider()
        st.markdown("#### OCR Preview")
        st.markdown(
            f'<div class="preview-box">{detail.preview_text}</div>',
            unsafe_allow_html=True,
        )


def render() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    entity_id = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
    if entity_id is None:
        _render_no_entity()
        return

    _render_header(str(entity_id))

    vm = DocumentsVM()
    search = _render_toolbar(vm)
    documents = vm.load_documents()

    st.divider()

    left, right = st.columns([3, 7])

    with left:
        _render_document_list(documents, search)

    with right:
        document_id = sm.get(SessionKeys.SELECTED_DOCUMENT_ID)

        if document_id is None:
            st.info("Select a document to view details.")
            return

        detail = vm.load_document(str(document_id))

        if detail is None:
            st.error("Document not found.")
            return

        _render_document_detail(detail)
