from __future__ import annotations

import hashlib

import streamlit as st

from ui.state import session_manager as sm
from ui.state.page_id import PageId
from ui.state.session_keys import SessionKeys
from ui.viewmodels.document_models import DocumentDetail, DocumentSummary
from ui.viewmodels.documents_vm import DocumentsVM

SUPPORTED_DOC_TYPES = [
    "passport",
    "id_card",
    "residence_permit",
    "bank_statement",
    "contract",
    "invoice",
    "certificate",
    "other",
]


def _render_toolbar(vm: DocumentsVM) -> str:
    col_upload, col_type, col_refresh, col_search = st.columns([3, 2, 1, 4])

    with col_type:
        doc_type = st.selectbox(
            "Document Type",
            SUPPORTED_DOC_TYPES,
            label_visibility="collapsed",
        )

    with col_upload:
        uploaded = st.file_uploader("Upload", label_visibility="collapsed")

    with col_refresh:
        if st.button("↺ Refresh"):
            sm.reset(SessionKeys.SELECTED_DOCUMENT_ID)
            st.rerun()

    with col_search:
        search = st.text_input(
            "Search", placeholder="Filter by name...", label_visibility="collapsed"
        )

    if uploaded:
        file_bytes = uploaded.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        last_hash = st.session_state.get("_last_uploaded_hash")

        if file_hash != last_hash:
            st.session_state["_last_uploaded_hash"] = file_hash
            with st.spinner(
                f"Processing **{uploaded.name}** — OCR & Extraction running..."
            ):
                result = vm.upload_document(file_bytes, uploaded.name, doc_type)

            if result.success:
                st.success(f"✅ Document processed successfully: **{uploaded.name}**")
                st.rerun()
            else:
                st.error(f"❌ Processing failed: {result.message}")

    return search


def _status_color(status: str) -> str:
    return {
        "pending": "🟡",
        "processing": "🔵",
        "processed": "🟢",
        "failed": "🔴",
    }.get(status, "⚪")


def _render_document_list(documents: tuple[DocumentSummary, ...], search: str) -> None:
    if not documents:
        st.info("No documents found.")
        return

    filtered = [
        d for d in documents if not search or search.lower() in d.file_name.lower()
    ]

    if not filtered:
        st.info("No documents match the filter.")
        return

    for doc in filtered:
        col_name, col_type, col_status, col_conf, col_action = st.columns(
            [4, 2, 2, 1, 1]
        )
        with col_name:
            st.write(doc.file_name)
        with col_type:
            st.caption(doc.document_type)
        with col_status:
            st.caption(f"{_status_color(doc.status)} {doc.status}")
        with col_conf:
            st.caption(f"{doc.confidence:.0%}" if doc.confidence else "—")
        with col_action:
            if st.button("View", key=f"view_{doc.document_id}"):
                sm.set(SessionKeys.SELECTED_DOCUMENT_ID, doc.document_id)
                st.rerun()


def _render_document_detail(detail: DocumentDetail) -> None:
    st.markdown(f"### {detail.file_name}")
    st.caption(
        f"{detail.document_type}  ·  "
        f"{_status_color(detail.status)} {detail.status}  ·  "
        f"{detail.created_at}"
    )
    st.divider()

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Pages", detail.page_count)
    with col_b:
        st.metric("Fields", detail.extracted_fields_count)
    with col_c:
        st.metric("Conflicts", detail.conflict_count)
    with col_d:
        st.metric(
            "Confidence",
            f"{detail.confidence:.0%}" if detail.confidence else "—",
        )

    if detail.review_required:
        st.warning("⚠️ Review required")

    if detail.preview_text:
        st.divider()
        st.markdown("#### Preview")
        st.write(detail.preview_text)

    if detail.status == "failed":
        st.error("❌ This document failed to process. Please re-upload or check logs.")


def render() -> None:
    entity_id = sm.get(SessionKeys.ACTIVE_ENTITY_ID)
    if entity_id is None:
        st.warning("⚠️ No active entity selected.")
        st.markdown(
            "Please go to **⚙️ Settings** to create or activate an entity first."
        )
        if st.button("⚙️ Go to Settings", type="primary"):
            sm.set(SessionKeys.CURRENT_PAGE, PageId.SETTINGS)
            st.rerun()
        return

    vm = DocumentsVM()
    documents = vm.load_documents()
    search = _render_toolbar(vm)
    st.divider()

    left, right = st.columns([3, 7])

    with left:
        st.subheader("Documents")
        _render_document_list(documents, search)

    with right:
        document_id: str | None = sm.get(SessionKeys.SELECTED_DOCUMENT_ID)

        if document_id is None:
            st.info("Select a document to view details.")
            return

        detail = vm.load_document(document_id)

        if detail is None:
            st.error(f"Document '{document_id}' not found.")
            return

        _render_document_detail(detail)
