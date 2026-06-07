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


def _render_noise_item(item: NoiseItem, vm: NoiseVM) -> None:
    title = f"{item.stage} · {item.status} · confidence {item.confidence:.2f}"

    with st.expander(title):
        st.caption(f"ID: {item.noise_id}")
        st.caption(f"Created: {item.created_at}")

        raw_text = st.text_area(
            "Raw text",
            value=item.raw_text,
            height=140,
            key=f"noise_raw_text_{item.noise_id}",
        )

        reason = st.text_input(
            "Reason",
            value=item.reason,
            key=f"noise_reason_{item.noise_id}",
        )

        confidence = st.slider(
            "Confidence",
            min_value=0.0,
            max_value=1.0,
            value=float(item.confidence),
            step=0.01,
            key=f"noise_confidence_{item.noise_id}",
        )

        metadata_text = st.text_area(
            "Metadata JSON",
            value=json.dumps(item.metadata, ensure_ascii=False, indent=2),
            height=120,
            key=f"noise_metadata_{item.noise_id}",
        )

        col_save, col_reviewed, col_reopen, col_ignore, col_delete = st.columns(5)

        with col_save:
            if st.button(
                "Save",
                key=f"noise_save_{item.noise_id}",
                use_container_width=True,
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

    st.subheader("Noise Pool")
    st.caption(
        "Unclear OCR or extraction fragments that need review, correction, or deletion."
    )

    st.metric("Open noise items", open_count)

    show_all = st.toggle("Show reviewed and ignored items", value=False)

    items = vm.load_all(limit=50) if show_all else vm.load_open(limit=20)

    if not items:
        st.info("No real noise items found.")
        return

    for item in items:
        _render_noise_item(item, vm)
