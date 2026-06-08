from __future__ import annotations

import html

import streamlit as st

from ui.components.review.noise_processing_panel import render_noise_processing_panel
from ui.state import session_manager as sm
from ui.state.session_keys import SessionKeys
from ui.viewmodels.review_models import (
    DecisionType,
    OwnerSelection,
    OwnerTarget,
    ReviewCaseDetail,
    ReviewCaseSummary,
)
from ui.viewmodels.review_vm import ReviewVM

_CSS = """
<style>
.review-title {
    color: #38bdf8;
    font-size: 2.2rem;
    font-weight: 900;
    margin-bottom: 0.2rem;
}
.review-subtitle {
    color: #94a3b8;
    font-size: 0.95rem;
    margin-bottom: 1.2rem;
}
.hero-box {
    background: linear-gradient(135deg, #020617 0%, #0f172a 55%, #082f49 100%);
    border: 1px solid #1e40af;
    border-radius: 20px;
    padding: 1.4rem;
    margin-bottom: 1rem;
}
.hero-title {
    color: #e0f2fe;
    font-size: 1.15rem;
    font-weight: 800;
    margin-bottom: 0.4rem;
}
.hero-text {
    color: #cbd5e1;
    font-size: 0.92rem;
}
.clean-state {
    background: linear-gradient(135deg, #052e16 0%, #064e3b 55%, #0f766e 100%);
    border: 1px solid #10b981;
    border-radius: 20px;
    padding: 1.4rem;
    margin-top: 1rem;
    margin-bottom: 1rem;
}
.clean-title {
    color: #d1fae5;
    font-size: 1.45rem;
    font-weight: 900;
    margin-bottom: 0.35rem;
}
.clean-text {
    color: #a7f3d0;
    font-size: 0.95rem;
}
.llm-box {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
    border: 1px solid #6366f1;
    border-radius: 16px;
    padding: 1rem;
    color: #c7d2fe;
    margin-top: 0.8rem;
}
.case-card {
    background: #020617;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 1rem;
    margin-bottom: 0.75rem;
}
.case-title {
    color: #f8fafc;
    font-size: 0.98rem;
    font-weight: 800;
    margin-bottom: 0.25rem;
}
.case-status {
    color: #94a3b8;
    font-size: 0.78rem;
    margin-bottom: 0.75rem;
}
.raw-box {
    background: #020617;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 1rem;
    margin-bottom: 1rem;
}
.raw-label {
    color: #94a3b8;
    font-size: 0.78rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.raw-value {
    color: #f8fafc;
    font-size: 0.98rem;
    margin-bottom: 0.65rem;
    overflow-wrap: anywhere;
}
.pill {
    display: inline-block;
    background: #082f49;
    color: #bae6fd;
    border: 1px solid #0369a1;
    border-radius: 999px;
    padding: 0.2rem 0.65rem;
    font-size: 0.75rem;
    font-weight: 800;
    margin-right: 0.3rem;
}
.trust-box {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 1rem;
    margin-bottom: 1rem;
}
.trust-title {
    color: #f8fafc;
    font-size: 1rem;
    font-weight: 900;
    margin-bottom: 0.35rem;
}
.trust-text {
    color: #94a3b8;
    font-size: 0.88rem;
}
</style>
"""


def _safe(value: object) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    if not text:
        return "—"
    return html.escape(text)


def _render_header() -> None:
    st.markdown(
        """
        <div class="review-title">Human Knowledge Review</div>
        <div class="review-subtitle">
        Validate uncertain facts before they become trusted knowledge in NASMI.
        </div>
        <div class="hero-box">
            <div class="hero-title">Review, trust, then reuse</div>
            <div class="hero-text">
            NASMI keeps noisy OCR results away from the final knowledge base.
            Only accepted facts can be used later by the personal AI assistant and auto-fill workflow.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_metrics(vm: ReviewVM) -> dict[str, int]:
    metrics = vm.load_metrics()

    col_a, col_b, col_c, col_d, col_e = st.columns(5)

    with col_a:
        st.metric("Pending Review", metrics["pending"])
    with col_b:
        st.metric("Visible Cases", metrics["visible"])
    with col_c:
        st.metric("Accepted Facts", metrics["accepted"])
    with col_d:
        st.metric("Rejected Noise", metrics["rejected"])
    with col_e:
        st.metric("LLM Hidden", metrics["hidden_for_llm"])

    if metrics["hidden_for_llm"] > 0:
        st.markdown(
            f"""
            <div class="llm-box">
            <b>{metrics["hidden_for_llm"]} low-confidence candidates are hidden.</b><br>
            The LLM-assisted cleanup layer can later re-check context, improve classification,
            normalize useful values, and upgrade reliable facts for human review.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return metrics


def _render_clean_state(metrics: dict[str, int]) -> None:
    st.markdown(
        f"""
        <div class="clean-state">
            <div class="clean-title">✅ No pending review cases</div>
            <div class="clean-text">
            The review queue is clean. NASMI has filtered noisy candidates and kept the accepted
            knowledge base ready for the assistant and future auto-fill.
            </div>
        </div>
        <div class="trust-box">
            <div class="trust-title">Current knowledge status</div>
            <div class="trust-text">
            Accepted facts: <b>{metrics["accepted"]}</b> ·
            Rejected noise: <b>{metrics["rejected"]}</b> ·
            Hidden for LLM cleanup: <b>{metrics["hidden_for_llm"]}</b>
            </div>
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
    label = _safe(case.label)
    status = _safe(case.status)

    st.markdown(
        f"""
        <div class="case-card">
            <div class="case-title">{label}</div>
            <div class="case-status">Status: {status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "Selected" if selected else "Open case",
        key=f"open_{case.case_id}",
        use_container_width=True,
        disabled=selected,
    ):
        sm.set(SessionKeys.SELECTED_REVIEW_CASE_ID, case.case_id)
        st.rerun()


def _render_bucketed_queue(
    bucketed: dict[str, tuple[ReviewCaseSummary, ...]],
) -> int:
    st.subheader("Review Queue")

    total = sum(len(items) for items in bucketed.values())
    if total == 0:
        st.info("No review cases match the current filters.")
        return total

    for bucket, cases in bucketed.items():
        with st.expander(
            f"{bucket} · {len(cases)} cases", expanded=bucket == "90% - 100%"
        ):
            if not cases:
                st.caption("No cases in this bucket.")
                continue

            for case in cases:
                _render_case_button(case)

    return total


def _render_case_header(detail: ReviewCaseDetail) -> None:
    st.markdown(f"### {_safe(detail.entity_name)}")

    col_ref, col_status, col_conf = st.columns(3)

    with col_ref:
        st.caption(f"Reference: {detail.document_reference or '—'}")
    with col_status:
        st.caption(f"Status: {detail.status}")
    with col_conf:
        st.caption(f"Confidence: {detail.confidence:.0%}")

    st.markdown(
        """
        <span class="pill">Human validation</span>
        <span class="pill">Evidence linked</span>
        <span class="pill">Knowledge candidate</span>
        """,
        unsafe_allow_html=True,
    )


def _render_raw_context(detail: ReviewCaseDetail) -> None:
    st.markdown(
        f"""
        <div class="raw-box">
            <div class="raw-label">Detected type</div>
            <div class="raw-value">{_safe(detail.fact_type)}</div>
            <div class="raw-label">Raw value from document</div>
            <div class="raw-value">{_safe(detail.raw_value)}</div>
            <div class="raw-label">Normalized value</div>
            <div class="raw-value">{_safe(detail.normalized_value)}</div>
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
        help="Choose the internal field used later by the assistant and auto-fill.",
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
        help="Accept only the real personal value, not labels or OCR noise.",
    )

    return selected_field.strip(), edited_value.strip()



def _render_owner_editor(detail: ReviewCaseDetail) -> OwnerSelection:
    st.markdown("#### Fact Owner")

    metadata = detail.metadata or {}
    owner_suggestion = metadata.get("owner_suggestion") if isinstance(metadata.get("owner_suggestion"), dict) else {}

    suggested_name = str(owner_suggestion.get("name") or "").strip()
    suggested_type = str(owner_suggestion.get("type") or "").strip()
    suggested_relation = str(owner_suggestion.get("relation_to_active_entity") or "").strip()

    target_labels = {
        OwnerTarget.ACTIVE_ENTITY: "My active profile",
        OwnerTarget.EXTERNAL_ENTITY: "External / other entity",
    }

    default_target = OwnerTarget.EXTERNAL_ENTITY if suggested_name else OwnerTarget.ACTIVE_ENTITY

    selected_target = st.radio(
        "Belongs to",
        options=[OwnerTarget.ACTIVE_ENTITY, OwnerTarget.EXTERNAL_ENTITY],
        index=[OwnerTarget.ACTIVE_ENTITY, OwnerTarget.EXTERNAL_ENTITY].index(default_target),
        format_func=lambda x: target_labels.get(x, str(x)),
        horizontal=True,
        key=f"owner_target_{detail.case_id}",
        help="Choose who this fact really belongs to. This prevents company/bank data from entering your personal profile.",
    )

    owner_types = [
        "person",
        "company",
        "bank",
        "university",
        "authority",
        "insurance_provider",
        "employer",
        "landlord",
        "property",
        "contract",
        "unknown_organization",
    ]

    relation_types = [
        "self",
        "document_issuer",
        "employer",
        "landlord",
        "bank",
        "university",
        "insurance_provider",
        "authority",
        "payment_receiver",
        "service_provider",
        "contract_party",
        "other",
    ]

    if selected_target == OwnerTarget.ACTIVE_ENTITY:
        st.info("This fact will be saved under your active profile.")
        return OwnerSelection(
            target=OwnerTarget.ACTIVE_ENTITY,
            owner_type="person",
            owner_name="",
            relation_type="self",
        )

    col_type, col_relation = st.columns(2)

    with col_type:
        default_type = suggested_type if suggested_type in owner_types else "company"
        owner_type = st.selectbox(
            "Owner type",
            options=owner_types,
            index=owner_types.index(default_type),
            key=f"owner_type_{detail.case_id}",
        )

    with col_relation:
        default_relation = suggested_relation if suggested_relation in relation_types else "other"
        relation_type = st.selectbox(
            "Relation to active profile",
            options=relation_types,
            index=relation_types.index(default_relation),
            key=f"relation_type_{detail.case_id}",
        )

    owner_name = st.text_input(
        "Owner name",
        value=suggested_name,
        placeholder="Example: TK, Sparkasse, ABC Immobilien GmbH, Ausländerbehörde...",
        key=f"owner_name_{detail.case_id}",
        help="If this value belongs to a company, bank, authority or another person, write its name here.",
    )

    return OwnerSelection(
        target=OwnerTarget.EXTERNAL_ENTITY,
        owner_type=owner_type.strip() or "unknown_organization",
        owner_name=owner_name.strip(),
        relation_type=relation_type.strip() or "other",
    )


def _render_metadata(detail: ReviewCaseDetail) -> None:
    with st.expander("Evidence and review context"):
        if not detail.metadata:
            st.caption("No metadata.")
            return

        st.json(detail.metadata)


def _render_conflict_viewer(detail: ReviewCaseDetail) -> None:
    st.markdown("#### Conflicts")

    if not detail.conflicts:
        st.success("No conflicts detected.")
        return

    for conflict in detail.conflicts:
        with st.expander(
            f"{conflict.field}  :  {conflict.value_a}  vs  {conflict.value_b}"
        ):
            for evidence in conflict.evidence:
                st.write(evidence.excerpt)


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
    owner_selection: OwnerSelection,
) -> None:
    st.divider()

    col_accept, col_save, col_reject = st.columns(3)

    with col_accept:
        if st.button(
            "Accept knowledge",
            type="primary",
            key=f"accept_{detail.case_id}",
            use_container_width=True,
        ):
            result = vm.submit_decision(
                detail.case_id,
                DecisionType.ACCEPT,
                edited_value=edited_value,
                edited_field=edited_field,
                owner_selection=owner_selection,
            )
            if result.success:
                _clear_selected_case()
                st.success("Accepted into trusted knowledge")
                st.rerun()
            else:
                st.error(result.error or result.message)

    with col_save:
        if st.button(
            "Save edit",
            key=f"edit_{detail.case_id}",
            use_container_width=True,
        ):
            result = vm.submit_decision(
                detail.case_id,
                DecisionType.EDIT,
                edited_value=edited_value,
                edited_field=edited_field,
                owner_selection=owner_selection,
            )
            if result.success:
                st.info("Edit saved")
                st.rerun()
            else:
                st.error(result.error or result.message)

    with col_reject:
        if st.button(
            "Reject as noise",
            key=f"reject_{detail.case_id}",
            use_container_width=True,
        ):
            result = vm.submit_decision(detail.case_id, DecisionType.REJECT)
            if result.success:
                _clear_selected_case()
                st.warning("Rejected as noise")
                st.rerun()
            else:
                st.error(result.error or result.message)


def _render_selected_case(vm: ReviewVM) -> None:
    case_id: str | None = sm.get(SessionKeys.SELECTED_REVIEW_CASE_ID)

    if case_id is None:
        st.info("Select a case from the review queue.")
        st.markdown(
            """
            <div class="trust-box">
                <div class="trust-title">Why review matters</div>
                <div class="trust-text">
                Accepted values become trusted personal knowledge.
                Rejected values stay out of the assistant and auto-fill workflow.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
    owner_selection = _render_owner_editor(detail)

    st.divider()
    _render_metadata(detail)

    st.divider()
    _render_conflict_viewer(detail)

    _render_decision_bar(detail, vm, edited_field, edited_value, owner_selection)


def render() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    vm = ReviewVM()

    _render_header()

    tab_review, tab_noise = st.tabs(["Review Queue", "Noise Processing"])

    with tab_review:
        metrics = _render_metrics(vm)
        st.divider()

        search, fact_type, include_low_value = _render_filters(vm)

        bucketed = vm.load_bucketed_queue(
            limit_per_bucket=20,
            include_low_value=include_low_value,
            search=search,
            fact_type=fact_type,
        )

        st.divider()

        total_visible_cases = sum(len(items) for items in bucketed.values())

        if metrics["pending"] == 0 and total_visible_cases == 0:
            _render_clean_state(metrics)
        else:
            left, right = st.columns([4, 6])

            with left:
                _render_bucketed_queue(bucketed)

            with right:
                _render_selected_case(vm)

    with tab_noise:
        render_noise_processing_panel()
