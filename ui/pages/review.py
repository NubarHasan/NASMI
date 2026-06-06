from __future__ import annotations

import streamlit as st

from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys
from ui.viewmodels.review_models import (
    DecisionType,
    ReviewCaseDetail,
    ReviewCaseSummary,
)
from ui.viewmodels.review_vm import ReviewVM


def _render_queue(queue: tuple[ReviewCaseSummary, ...]) -> None:
    st.subheader("Review Queue")
    for case in queue:
        col_label, col_status, col_action = st.columns([4, 2, 2])
        with col_label:
            st.write(case.label)
        with col_status:
            st.caption(case.status)
        with col_action:
            if st.button("Open", key=f"open_{case.case_id}"):
                sm.set(SessionKeys.SELECTED_REVIEW_CASE_ID, case.case_id)


def _render_case_header(detail: ReviewCaseDetail) -> None:
    st.markdown(f"### {detail.entity_name}")
    col_ref, col_status = st.columns(2)
    with col_ref:
        st.caption(f"Ref: {detail.document_reference}")
    with col_status:
        st.caption(f"Status: {detail.status}")


def _render_suggestion_table(detail: ReviewCaseDetail) -> None:
    st.markdown("#### Suggestions")
    if not detail.suggestions:
        st.info("No suggestions.")
        return
    for s in detail.suggestions:
        col_field, col_value, col_status = st.columns([3, 4, 2])
        with col_field:
            st.write(s.field)
        with col_value:
            st.write(s.value)
        with col_status:
            st.caption(s.status)


def _render_evidence_panel(evidence: tuple) -> None:
    for ev in evidence:
        with st.expander(
            f"{ev.source}  —  p.{ev.page or '—'}  ({ev.confidence or '—'})"
        ):
            st.write(ev.excerpt)


def _render_conflict_viewer(detail: ReviewCaseDetail) -> None:
    st.markdown("#### Conflicts")
    if not detail.conflicts:
        st.success("No conflicts.")
        return
    for c in detail.conflicts:
        with st.expander(f"{c.field}  :  {c.value_a}  vs  {c.value_b}"):
            _render_evidence_panel(c.evidence)


def _render_decision_bar(detail: ReviewCaseDetail, vm: ReviewVM) -> None:
    st.divider()
    col_accept, col_reject, col_edit = st.columns(3)
    with col_accept:
        if st.button("Accept", type="primary", key=f"accept_{detail.case_id}"):
            vm.submit_decision(detail.case_id, DecisionType.ACCEPT)
            st.success("Accepted")
    with col_reject:
        if st.button("Reject", key=f"reject_{detail.case_id}"):
            vm.submit_decision(detail.case_id, DecisionType.REJECT)
            st.warning("Rejected")
    with col_edit:
        if st.button("Edit", key=f"edit_{detail.case_id}"):
            vm.submit_decision(detail.case_id, DecisionType.EDIT)
            st.info("Marked for editing")


def render() -> None:
    vm = ReviewVM()
    queue = vm.load_queue()

    left, right = st.columns([3, 7])

    with left:
        _render_queue(queue)

    with right:
        case_id: str | None = sm.get(SessionKeys.SELECTED_REVIEW_CASE_ID)

        if case_id is None:
            st.info("Select a case from the queue.")
            return

        detail = vm.load_case_detail(case_id)

        if detail is None:
            st.error(f"Case '{case_id}' not found.")
            return

        _render_case_header(detail)
        st.divider()
        _render_suggestion_table(detail)
        st.divider()
        _render_conflict_viewer(detail)
        _render_decision_bar(detail, vm)
