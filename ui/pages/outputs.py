from __future__ import annotations

import streamlit as st

from output.output_format import OutputFormat
from output.output_type import OutputType
from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys
from ui.viewmodels.output_models import OutputDetail, OutputSummary
from ui.viewmodels.outputs_vm import OutputsVM


def _load_outputs(vm: OutputsVM) -> tuple[OutputSummary, ...]:
    cached = sm.get(SessionKeys.OUTPUT_LIST)
    if cached is not None:
        return tuple(cached)
    initial = vm.initial_outputs()
    sm.set(SessionKeys.OUTPUT_LIST, list(initial))
    return initial


def _status_badge(succeeded: bool) -> str:
    return "✅ Ready" if succeeded else "❌ Failed"


def _render_generate_form(vm: OutputsVM, outputs: tuple[OutputSummary, ...]) -> None:
    st.subheader("Generate Output")

    type_options = vm.supported_types()
    type_labels = [vm.label_for(t) for t in type_options]

    selected_label = st.selectbox("Output Type", options=type_labels, index=0)
    selected_type: OutputType = type_options[type_labels.index(selected_label)]

    st.caption(vm.description_for(selected_type))

    if st.button("Generate", type="primary"):
        result, updated = vm.generate(selected_type, outputs, OutputFormat.JSON)
        if result.success:
            sm.set(SessionKeys.OUTPUT_LIST, list(updated))
            st.success(f"Generated: {result.detail.label}")
            st.rerun()
        else:
            st.error(result.error)


def _render_output_list(
    vm: OutputsVM,
    outputs: tuple[OutputSummary, ...],
) -> None:
    st.subheader("Generated Outputs")

    if not outputs:
        st.info("No outputs generated yet.")
        return

    for summary in outputs:
        col_label, col_type, col_fmt, col_status, col_action = st.columns(
            [3, 2, 1, 2, 1]
        )
        with col_label:
            st.write(summary.label)
        with col_type:
            st.write(summary.output_type.value)
        with col_fmt:
            st.write(summary.output_format.value.upper())
        with col_status:
            st.write(_status_badge(summary.succeeded))
        with col_action:
            if st.button("View", key=f"view_{summary.output_id}"):
                sm.set(SessionKeys.SELECTED_OUTPUT_ID, summary.output_id)
                st.rerun()


def _render_output_detail(
    vm: OutputsVM,
    output_id: str,
    outputs: tuple[OutputSummary, ...],
) -> None:
    detail: OutputDetail | None = vm.get_detail(output_id, outputs)

    if detail is None:
        st.warning("Output not found.")
        sm.reset(SessionKeys.SELECTED_OUTPUT_ID)
        return

    if st.button("← Back"):
        sm.reset(SessionKeys.SELECTED_OUTPUT_ID)
        st.rerun()

    st.subheader(detail.label)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Type", detail.output_type.value)
    with col_b:
        st.metric("Format", detail.output_format.value.upper())
    with col_c:
        st.metric("Status", _status_badge(detail.succeeded))

    if detail.succeeded and detail.file_path:
        st.code(detail.file_path, language=None)
        st.caption("File path shown above. Download available after pipeline run.")
    else:
        st.error("This output failed to generate.")


def render() -> None:
    st.title("Outputs")

    vm = OutputsVM()
    outputs = _load_outputs(vm)
    selected_id: str | None = sm.get(SessionKeys.SELECTED_OUTPUT_ID)

    if selected_id:
        _render_output_detail(vm, selected_id, outputs)
    else:
        _render_generate_form(vm, outputs)
        st.divider()
        _render_output_list(vm, outputs)
