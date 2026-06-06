from __future__ import annotations

import streamlit as st

from core.time import format_timestamp
from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys
from ui.viewmodels.audit_models import (
    AuditEntryDetail,
    AuditEntrySummary,
    AuditVerificationSummary,
)
from ui.viewmodels.audit_vm import AuditVM

_vm = AuditVM()


def _load_state() -> (
    tuple[list[AuditEntrySummary], list[AuditEntryDetail], AuditVerificationSummary]
):
    chain = sm.get(SessionKeys.AUDIT_CHAIN)
    result = sm.get(SessionKeys.AUDIT_RESULT)
    if chain is None or result is None:
        chain, result = _vm.refresh()
        sm.set(SessionKeys.AUDIT_CHAIN, chain)
        sm.set(SessionKeys.AUDIT_RESULT, result)
    summaries = _vm.get_summaries(chain)
    details = _vm.get_details(chain)
    verification = _vm.get_verification_summary(result)
    return summaries, details, verification


def _refresh_state() -> None:
    chain, result = _vm.refresh()
    sm.set(SessionKeys.AUDIT_CHAIN, chain)
    sm.set(SessionKeys.AUDIT_RESULT, result)
    sm.set(SessionKeys.AUDIT_SELECTED, None)


def _render_integrity_status(summary: AuditVerificationSummary) -> None:
    st.subheader("Integrity Status")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if summary.is_valid:
            st.success("✅ Valid")
        else:
            st.error("❌ Invalid")
    with col2:
        st.metric("Chain Length", summary.chain_length)
    with col3:
        st.metric("Verified Entries", summary.verified_entries)
    with col4:
        ts = format_timestamp(summary.verified_at)[:19].replace("T", " ")
        st.caption(f"Verified at\n{ts}")


def _render_violations(summary: AuditVerificationSummary) -> None:
    if not summary.violations:
        return
    st.subheader("⚠️ Violations")
    for v in summary.violations:
        idx_label = str(v.index) if v.index is not None else "N/A"
        with st.expander(f"[{v.kind}] — index: {idx_label}", expanded=True):
            st.caption(v.detail)


def _render_timeline(
    summaries: list[AuditEntrySummary],
    details: list[AuditEntryDetail],
) -> None:
    st.subheader("Timeline")
    if not summaries:
        st.info("No audit entries found.")
        return
    for i, (summary, detail) in enumerate(zip(summaries, details, strict=False)):
        ts = format_timestamp(summary.occurred_at)[:19].replace("T", " ")
        actor_tag = f" _(by {summary.actor})_" if summary.actor else ""
        label = (
            f"`{ts}` — **{summary.event_type.value}** — {summary.message}{actor_tag}"
        )
        if st.button(label, key=f"audit_entry_{i}", use_container_width=True):
            sm.set(SessionKeys.AUDIT_SELECTED, detail)
            st.rerun()


def _render_entry_detail(detail: AuditEntryDetail) -> None:
    st.subheader("Entry Detail")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Audit ID:** `{detail.audit_id}`")
        st.markdown(f"**Event Type:** `{detail.event_type.value}`")
        ts = format_timestamp(detail.occurred_at)[:19].replace("T", " ")
        st.markdown(f"**Occurred At:** `{ts}`")
        st.markdown(f"**Message:** {detail.message}")
        st.markdown(f"**Actor:** {detail.actor or '—'}")
    with col2:
        st.markdown(
            f"**Job ID:** `{detail.job_id}`" if detail.job_id else "**Job ID:** —"
        )
        st.markdown(
            f"**Subject ID:** `{detail.subject_id}`"
            if detail.subject_id
            else "**Subject ID:** —"
        )
        st.markdown(
            f"**Previous Hash:** `{detail.previous_hash}`"
            if detail.previous_hash
            else "**Previous Hash:** _(genesis)_"
        )
        st.markdown(f"**Entry Hash:** `{detail.entry_hash}`")
    if detail.metadata:
        st.markdown("**Metadata:**")
        st.json(detail.metadata)
    else:
        st.markdown("**Metadata:** —")
    if st.button("✖ Close", key="audit_close_detail"):
        sm.set(SessionKeys.AUDIT_SELECTED, None)
        st.rerun()


def render() -> None:
    st.title("🔐 Audit Trail")
    col_refresh, _ = st.columns([1, 9])
    with col_refresh:
        if st.button("🔄 Refresh", key="audit_refresh"):
            _refresh_state()
            st.rerun()
    summaries, details, verification = _load_state()
    st.divider()
    _render_integrity_status(verification)
    if verification.violations:
        st.divider()
        _render_violations(verification)
    st.divider()
    _render_timeline(summaries, details)
    selected: AuditEntryDetail | None = sm.get(SessionKeys.AUDIT_SELECTED)
    if selected is not None:
        st.divider()
        _render_entry_detail(selected)
