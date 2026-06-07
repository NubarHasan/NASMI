from __future__ import annotations

import streamlit as st

from ui.components.review.noise_processing_panel import render_noise_processing_panel
from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys
from ui.viewmodels.review_models import (
    DecisionType,
    ReviewCaseDetail,
    ReviewCaseSummary,
)
from ui.viewmodels.review_vm import ReviewVM

_CSS = """
<style>
.review-title {
    color: #38bdf8;
    font-size: 2rem;
    font-weight: 900;
    margin-bottom: 0.2rem;
}
.review-subtitle {
    color: #94a3b8;
    font-size: 0.9rem;
    margin-bottom: 1rem;
}
.llm-box {
    background: #1e1b4b;
    border: 1px solid #4338ca;
    border-radius: 14px;
    padding: 1rem;
    color: #c7d2fe;
}
.raw-box {
    background: #020617;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 1rem;
    margin-bottom: 1rem;
}
.raw-label {
    color: #94a3b8;
    font-size: 0.8rem;
    font-weight: 700;
}
.raw-value {
    color: #f8fafc;
    font-size: 0.95rem;
    margin-bottom: 0.5rem;
}
</style>
"""


def _render_header() -> None:
    st.markdown(
        """
        <div class="review-title">Human Knowledge Review</div>
        <div class="review-subtitle">
        Correct the canonical field and the real value before accepting knowledge into NASMI.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_metrics(vm: ReviewVM) -> None:
    metrics = vm.load_metrics()

    col_a, col_b, col_c, col_d, col_e = st.columns(5)

    with col_a:
        st.metric("Pending", metrics["pending"])
    with col_b:
        st.metric("Visible ≥ 50%", metrics["visible"])
    with col_c:
        st.metric("Accepted", metrics["accepted"])
    with col_d:
        st.metric("Rejected", metrics["rejected"])
    with col_e:
        st.metric("Hidden for LLM", metrics["hidden_for_llm"])

    if metrics["hidden_for_llm"] > 0:
        st.markdown(
            f"""
            <div class="llm-box">
            {metrics["hidden_for_llm"]} low-confidence or low-value cases are hidden from the user.
            Later, the LLM cleanup stage can decode, normalize, and upgrade useful cases above 50% confidence.
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_filters(vm: ReviewVM) -> tuple[str, str, bool]:
    fact_types = vm.load_fact_types()

    col_search, col_type, col_low = st.columns([3, 2, 2])

    with col_search:
        search = st.text_input(
            "Search",
            placeholder="Search value or fact type...",
            label_visibility="collapsed",
            key="review_search",
        )

    with col_type:
        selected_type = st.selectbox(
            "Fact type",
            fact_types,
            label_visibility="collapsed",
            key="review_fact_type",
        )

    with col_low:
        include_low_value = st.checkbox(
            "Show low-value",
            value=False,
            key="review_include_low_value",
        )

    return search, selected_type, include_low_value


def _render_case_button(case: ReviewCaseSummary) -> None:
    selected = sm.get(SessionKeys.SELECTED_REVIEW_CASE_ID) == case.case_id

    with st.container(border=True):
        st.markdown(f"**{case.label}**")
        st.caption(str(case.status))

        if st.button(
            "Selected" if selected else "Open",
            key=f"open_{case.case_id}",
            use_container_width=True,
            disabled=selected,
        ):
            sm.set(SessionKeys.SELECTED_REVIEW_CASE_ID, case.case_id)
            st.rerun()


def _render_bucketed_queue(
    bucketed: dict[str, tuple[ReviewCaseSummary, ...]],
) -> None:
    st.subheader("Confidence Buckets")

    total = sum(len(items) for items in bucketed.values())
    if total == 0:
        st.info("No review cases above 50% confidence with the current filters.")
        return

    for bucket, cases in bucketed.items():
        with st.expander(
            f"{bucket} · {len(cases)} cases", expanded=bucket == "90% - 100%"
        ):
            if not cases:
                st.caption("No cases in this bucket.")
                continue

            for case in cases:
                _render_case_button(case)


def _render_case_header(detail: ReviewCaseDetail) -> None:
    st.markdown(f"### {detail.entity_name}")

    col_ref, col_status, col_conf = st.columns(3)

    with col_ref:
        st.caption(f"Ref: {detail.document_reference or '—'}")
    with col_status:
        st.caption(f"Status: {detail.status}")
    with col_conf:
        st.caption(f"Confidence: {detail.confidence:.0%}")


def _render_raw_context(detail: ReviewCaseDetail) -> None:
    st.markdown(
        f"""
        <div class="raw-box">
            <div class="raw-label">Detected type</div>
            <div class="raw-value">{detail.fact_type or "—"}</div>
            <div class="raw-label">Raw value from document</div>
            <div class="raw-value">{detail.raw_value or "—"}</div>
            <div class="raw-label">Normalized value</div>
            <div class="raw-value">{detail.normalized_value or "—"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_knowledge_editor(
    detail: ReviewCaseDetail,
    vm: ReviewVM,
) -> tuple[str, str]:
    st.markdown("#### Correct Knowledge")

    options = list(detail.field_options)
    current = detail.canonical_field if detail.canonical_field in options else "other"
    index = options.index(current) if current in options else options.index("other")

    labels = {field: f"{field} — {vm.field_label(field)}" for field in options}

    selected_field = st.selectbox(
        "Canonical field",
        options=options,
        index=index,
        format_func=lambda x: labels.get(x, x),
        key=f"canonical_field_{detail.case_id}",
        help="Choose the real internal knowledge field used later for form autofill.",
    )

    default_value = ""
    if detail.suggestions:
        default_value = detail.suggestions[0].value
    if not default_value:
        default_value = detail.normalized_value or detail.raw_value

    edited_value = st.text_input(
        "Correct value",
        value=default_value,
        key=f"value_{detail.case_id}",
        help="This must be the real value, not the German label.",
    )

    return selected_field.strip(), edited_value.strip()


def _render_metadata(detail: ReviewCaseDetail) -> None:
    with st.expander("Review context"):
        if not detail.metadata:
            st.caption("No metadata.")
            return

        st.json(detail.metadata)


def _render_conflict_viewer(detail: ReviewCaseDetail) -> None:
    st.markdown("#### Conflicts")

    if not detail.conflicts:
        st.success("No conflicts.")
        return

    for c in detail.conflicts:
        with st.expander(f"{c.field}  :  {c.value_a}  vs  {c.value_b}"):
            for ev in c.evidence:
                st.write(ev.excerpt)


def _clear_selected_case() -> None:
    try:
        sm.reset(SessionKeys.SELECTED_REVIEW_CASE_ID)
    except Exception:
        sm.set(SessionKeys.SELECTED_REVIEW_CASE_ID, None)


def _render_decision_bar(
    detail: ReviewCaseDetail,
    vm: ReviewVM,
    edited_field: str,
    edited_value: str,
) -> None:
    st.divider()

    col_accept, col_save, col_reject = st.columns(3)

    with col_accept:
        if st.button(
            "Accept knowledge", type="primary", key=f"accept_{detail.case_id}"
        ):
            result = vm.submit_decision(
                detail.case_id,
                DecisionType.ACCEPT,
                edited_value=edited_value,
                edited_field=edited_field,
            )
            if result.success:
                _clear_selected_case()
                st.success("Accepted as knowledge")
                st.rerun()
            else:
                st.error(result.error or result.message)

    with col_save:
        if st.button("Save edit", key=f"edit_{detail.case_id}"):
            result = vm.submit_decision(
                detail.case_id,
                DecisionType.EDIT,
                edited_value=edited_value,
                edited_field=edited_field,
            )
            if result.success:
                st.info("Edit saved")
                st.rerun()
            else:
                st.error(result.error or result.message)

    with col_reject:
        if st.button("Reject", key=f"reject_{detail.case_id}"):
            result = vm.submit_decision(detail.case_id, DecisionType.REJECT)
            if result.success:
                _clear_selected_case()
                st.warning("Rejected")
                st.rerun()
            else:
                st.error(result.error or result.message)


def _render_selected_case(vm: ReviewVM) -> None:
    case_id: str | None = sm.get(SessionKeys.SELECTED_REVIEW_CASE_ID)

    if case_id is None:
        st.info("Select a case from the confidence buckets.")
        return

    detail = vm.load_case_detail(case_id)

    if detail is None:
        st.error(f"Case '{case_id}' not found.")
        return

    _render_case_header(detail)
    st.divider()

    _render_raw_context(detail)

    edited_field, edited_value = _render_knowledge_editor(detail, vm)

    st.divider()
    _render_metadata(detail)

    st.divider()
    _render_conflict_viewer(detail)

    _render_decision_bar(detail, vm, edited_field, edited_value)


def render() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    vm = ReviewVM()

    _render_header()

    tab_review, tab_noise = st.tabs(["Review Queue", "Noise Pool"])

    with tab_review:
        _render_metrics(vm)
        st.divider()

        search, fact_type, include_low_value = _render_filters(vm)

        bucketed = vm.load_bucketed_queue(
            limit_per_bucket=20,
            include_low_value=include_low_value,
            search=search,
            fact_type=fact_type,
        )

        st.divider()

        left, right = st.columns([4, 6])

        with left:
            _render_bucketed_queue(bucketed)

        with right:
            _render_selected_case(vm)

    with tab_noise:
        render_noise_processing_panel()
