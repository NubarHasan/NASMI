from __future__ import annotations

import json

import streamlit as st

from infrastructure.db.repositories.sqlite_noise_repository import NoiseItem
from ui.viewmodels.noise_vm import NoiseActionResult, NoiseVM


def _render_result(result: NoiseActionResult) -> None:
    if result.success:
        st.success(result.message)
        st.rerun()
    else:
        st.error(result.error or result.message)


def _status_label(status: str) -> str:
    value = str(status or "").strip().lower()

    if value == "open":
        return "Ready for LLM"
    if value == "processing":
        return "LLM processing"
    if value == "promoted":
        return "Moved to Review"
    if value == "reviewed":
        return "Reviewed"
    if value == "ignored":
        return "Ignored"
    if value == "failed":
        return "Failed"

    return value or "Unknown"


def _render_status_summary(items: tuple[NoiseItem, ...], open_count: int) -> None:
    processing = sum(1 for item in items if item.status == "processing")
    failed = sum(1 for item in items if item.status == "failed")
    promoted = sum(1 for item in items if item.status == "promoted")

    col_a, col_b, col_c, col_d = st.columns(4)

    with col_a:
        st.metric("Open noise", open_count)
    with col_b:
        st.metric("Processing", processing)
    with col_c:
        st.metric("Promoted", promoted)
    with col_d:
        st.metric("Failed", failed)

    if processing > 0:
        st.info("LLM cleanup is still processing. Keep reviewing OCR results above.")
    elif promoted > 0:
        st.success("Some LLM results were moved into the Review Queue.")
    elif open_count > 0:
        st.warning("Noise is waiting for LLM cleanup or manual review.")


def _render_noise_item(item: NoiseItem, vm: NoiseVM) -> None:
    title = (
        f"{_status_label(item.status)} · {item.stage} · "
        f"confidence {item.confidence:.2f}"
    )

    expanded = item.status in {"open", "processing", "failed"}

    with st.expander(title, expanded=expanded):
        st.caption(f"ID: {item.noise_id}")
        st.caption(f"Created: {item.created_at}")
        st.caption(f"Document: {item.document_id or '—'}")
        st.caption(f"Source: {item.source_id or '—'}")

        raw_text = st.text_area(
            "Raw text",
            value=item.raw_text,
            height=160,
            key=f"noise_raw_text_{item.noise_id}",
            disabled=item.status == "processing",
        )

        reason = st.text_input(
            "Reason",
            value=item.reason,
            key=f"noise_reason_{item.noise_id}",
            disabled=item.status == "processing",
        )

        confidence = st.slider(
            "Confidence",
            min_value=0.0,
            max_value=1.0,
            value=float(item.confidence),
            step=0.01,
            key=f"noise_confidence_{item.noise_id}",
            disabled=item.status == "processing",
        )

        metadata_text = st.text_area(
            "Metadata JSON",
            value=json.dumps(item.metadata, ensure_ascii=False, indent=2),
            height=120,
            key=f"noise_metadata_{item.noise_id}",
            disabled=item.status == "processing",
        )

        if item.status == "processing":
            st.info("This item is currently being processed by the LLM.")
            return

        if item.status == "promoted":
            st.success("This noise item was already converted into Review Queue cases.")

        col_llm, col_save, col_reviewed, col_reopen, col_ignore, col_delete = (
            st.columns(6)
        )

        with col_llm:
            can_process = item.status in {"open", "failed"}
            if st.button(
                "Process with LLM",
                key=f"noise_llm_{item.noise_id}",
                use_container_width=True,
                disabled=not can_process,
            ):
                result = vm.process_with_llm(item.noise_id)
                _render_result(result)

        with col_save:
            if st.button(
                "Save",
                key=f"noise_save_{item.noise_id}",
                use_container_width=True,
                disabled=item.status == "promoted",
            ):
                result = vm.save_edit(
                    noise_id=item.noise_id,
                    raw_text=raw_text,
                    reason=reason,
                    confidence=confidence,
                    metadata_text=metadata_text,
                )
                _render_result(result)

        with col_reviewed:
            if st.button(
                "Reviewed",
                key=f"noise_reviewed_{item.noise_id}",
                use_container_width=True,
            ):
                _render_result(vm.mark_reviewed(item.noise_id))

        with col_reopen:
            if st.button(
                "Reopen",
                key=f"noise_reopen_{item.noise_id}",
                use_container_width=True,
            ):
                _render_result(vm.reopen(item.noise_id))

        with col_ignore:
            if st.button(
                "Ignore",
                key=f"noise_ignore_{item.noise_id}",
                use_container_width=True,
            ):
                _render_result(vm.ignore(item.noise_id))

        with col_delete:
            if st.button(
                "Delete",
                key=f"noise_delete_{item.noise_id}",
                use_container_width=True,
            ):
                _render_result(vm.delete(item.noise_id))


def render_noise_processing_panel() -> None:
    vm = NoiseVM()
    open_count = vm.count_open()

    st.subheader("Noise Processing")
    st.caption(
        "OCR review stays available immediately. LLM cleanup can process noisy fragments separately and move useful results into the Review Queue."
    )

    col_refresh, col_toggle = st.columns([1, 2])

    with col_refresh:
        if st.button("Refresh status", use_container_width=True):
            st.rerun()

    with col_toggle:
        show_all = st.toggle("Show reviewed and ignored items", value=False)

    items = vm.load_all(limit=50) if show_all else vm.load_open(limit=20)

    _render_status_summary(items, open_count)

    if not items:
        st.info("No noise items found.")
        return

    st.divider()

    for item in items:
        _render_noise_item(item, vm)
