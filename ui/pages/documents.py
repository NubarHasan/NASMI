from __future__ import annotations

import streamlit as st

from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys
from ui.viewmodels.document_models import DocumentDetail, DocumentSummary, DocumentType
from ui.viewmodels.documents_vm import DocumentsVM


def _render_toolbar(vm: DocumentsVM) -> str:
    col_upload, col_refresh, col_search = st.columns([2, 1, 4])
    with col_upload:
        uploaded = st.file_uploader("Upload", label_visibility="collapsed")
        if uploaded:
            result = vm.upload_document(uploaded.name, DocumentType.OTHER)
            if result.success:
                st.success(f"Uploaded: {uploaded.name}")
            else:
                st.error("Upload failed.")
    with col_refresh:
        if st.button("Refresh"):
            sm.reset(SessionKeys.SELECTED_DOCUMENT_ID)
            st.rerun()
    with col_search:
        return st.text_input(
            "Search", placeholder="Filter by name...", label_visibility="collapsed"
        )
    return ""


def _render_document_list(documents: tuple[DocumentSummary, ...], search: str) -> None:
    filtered = (
        d for d in documents if not search or search.lower() in d.file_name.lower()
    )
    for doc in filtered:
        col_name, col_type, col_status, col_conf, col_action = st.columns(
            [4, 2, 2, 1, 1]
        )
        with col_name:
            st.write(doc.file_name)
        with col_type:
            st.caption(doc.document_type)
        with col_status:
            st.caption(doc.status)
        with col_conf:
            st.caption(f"{doc.confidence:.0%}" if doc.confidence else "—")
        with col_action:
            if st.button("View", key=f"view_{doc.document_id}"):
                sm.set(SessionKeys.SELECTED_DOCUMENT_ID, doc.document_id)


def _render_document_detail(detail: DocumentDetail) -> None:
    st.markdown(f"### {detail.file_name}")
    st.caption(f"{detail.document_type}  ·  {detail.status}  ·  {detail.created_at}")
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
            "Confidence", f"{detail.confidence:.0%}" if detail.confidence else "—"
        )

    if detail.review_required:
        st.warning("Review required")

    st.divider()
    st.markdown("#### Preview")
    st.write(detail.preview_text)


def render() -> None:
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
