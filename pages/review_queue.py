from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header(
    "✋",
    "Review Queue",
    "Human-in-the-loop validation — Critical · Suspicious · Low Risk",
)


# ── Renderers ─────────────────────────────────────────
def _render_review_item(item: dict[str, object], unique_key: str) -> None:
    priority = str(item["priority"])
    priority_color = (
        "#ef9a9a"
        if priority == "critical"
        else "#ffcc80" if priority == "suspicious" else "#90a4ae"
    )
    st.markdown(
        f"<div class='nasmi-card' style='border-left:3px solid {priority_color};'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;'>"
        f"<span style='font-weight:700;color:#e3f2fd;font-size:0.95rem;'>{item['field']}</span>"
        f"{badge(priority.upper(), 'conflict' if priority == 'critical' else 'pending')}"
        f"{badge(str(item['type']), str(item['status']))}"
        f"</div>"
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;margin:0.4rem 0;'>"
        f"<div style='background:#0d1b2a;border-radius:6px;padding:0.6rem;'>"
        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;margin-bottom:0.2rem;'>Extracted Value</div>"
        f"<div style='font-size:0.9rem;font-weight:600;color:#e3f2fd;'>{item['value']}</div>"
        f"<div style='font-size:0.7rem;color:#37474f;margin-top:0.2rem;'>"
        f"📄 {item['source']} · 🔍 OCR: {item['confidence']}%</div>"
        f"</div>"
        f"<div style='background:#0d1b2a;border-radius:6px;padding:0.6rem;'>"
        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;margin-bottom:0.2rem;'>Current Known Value</div>"
        f"<div style='font-size:0.9rem;font-weight:600;color:#90a4ae;'>{item['known_value']}</div>"
        f"<div style='font-size:0.7rem;color:#37474f;margin-top:0.2rem;'>"
        f"📅 Last updated: {item['last_updated']}</div>"
        f"</div>"
        f"</div>"
        f"<div style='font-size:0.75rem;color:#546e7a;margin-top:0.2rem;'>"
        f"⚠️ {item['reason']}"
        f"</div>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    col_accept, col_edit, col_reject, col_skip = st.columns([2, 2, 2, 1])

    with col_accept:
        if st.button("✅ Accept", key=f"accept_{unique_key}", use_container_width=True):
            st.toast(f"Accepted: {item['value']}", icon="✅")

    with col_edit:
        if st.button(
            "✏️ Edit & Accept", key=f"edit_{unique_key}", use_container_width=True
        ):
            st.session_state[f"edit_open_{unique_key}"] = True

    with col_reject:
        if st.button("❌ Reject", key=f"reject_{unique_key}", use_container_width=True):
            st.toast(f"Rejected: {item['field']}", icon="❌")

    with col_skip:
        if st.button("⏭", key=f"skip_{unique_key}", use_container_width=True):
            st.toast("Skipped", icon="⏭")

    if st.session_state.get(f"edit_open_{unique_key}"):
        edited = st.text_input(
            "Corrected value",
            value=str(item["value"]),
            key=f"edit_val_{unique_key}",
        )
        if st.button("💾 Save", key=f"save_edit_{unique_key}"):
            if edited.strip():
                st.toast(f"Saved: {edited}", icon="💾")
                st.session_state[f"edit_open_{unique_key}"] = False
            else:
                st.warning("Value cannot be empty.")

    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)


def _empty_state(msg: str = "Queue is empty.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:3rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Controls ──────────────────────────────────────────
col_pri, col_type, col_search, col_bulk = st.columns([2, 2, 3, 2])

with col_pri:
    pri_filter = st.selectbox(
        "Priority",
        ["All", "critical", "suspicious", "low"],
        label_visibility="collapsed",
        key="rq_priority",
    )

with col_type:
    type_filter = st.selectbox(
        "Type",
        ["All", "PERSON", "DATE", "ADDRESS", "ID", "FINANCE", "GPE", "OTHER"],
        label_visibility="collapsed",
        key="rq_type",
    )

with col_search:
    rq_search = st.text_input(
        "Search queue",
        placeholder="Search by field, value, source...",
        label_visibility="collapsed",
        key="rq_search",
    )

with col_bulk:
    if st.button("✅ Accept All Low Risk", use_container_width=True):
        st.toast("All low-risk items accepted", icon="✅")

st.divider()

# ── Stats ─────────────────────────────────────────────
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Total Pending", "—")
s2.metric("Critical", "—")
s3.metric("Suspicious", "—")
s4.metric("Low Risk", "—")
s5.metric("Reviewed Today", "—")

st.divider()

# ── Mock Queue ────────────────────────────────────────
mock_queue: list[dict[str, object]] = [
    {
        "field": "Full Name",
        "value": "—",
        "known_value": "—",
        "type": "PERSON",
        "source": "—",
        "confidence": 0,
        "priority": "critical",
        "status": "pending",
        "last_updated": "—",
        "reason": "Frozen field — manual review required before any update.",
    },
    {
        "field": "IBAN",
        "value": "—",
        "known_value": "—",
        "type": "FINANCE",
        "source": "—",
        "confidence": 0,
        "priority": "critical",
        "status": "pending",
        "last_updated": "—",
        "reason": "Conflict detected — value differs from existing record.",
    },
    {
        "field": "Address",
        "value": "—",
        "known_value": "—",
        "type": "ADDRESS",
        "source": "—",
        "confidence": 0,
        "priority": "suspicious",
        "status": "pending",
        "last_updated": "—",
        "reason": "Low OCR confidence — extraction may be inaccurate.",
    },
    {
        "field": "Phone Number",
        "value": "—",
        "known_value": "—",
        "type": "OTHER",
        "source": "—",
        "confidence": 0,
        "priority": "low",
        "status": "pending",
        "last_updated": "—",
        "reason": "New field — no existing value to compare against.",
    },
    {
        "field": "Tax ID",
        "value": "—",
        "known_value": "—",
        "type": "ID",
        "source": "—",
        "confidence": 0,
        "priority": "suspicious",
        "status": "pending",
        "last_updated": "—",
        "reason": "Partial match — extracted value may be incomplete.",
    },
]

# ── Filter Logic ──────────────────────────────────────
filtered: list[dict[str, object]] = list(mock_queue)

if pri_filter != "All":
    filtered = [i for i in filtered if i["priority"] == pri_filter]

if type_filter != "All":
    filtered = [i for i in filtered if i["type"] == type_filter]

if rq_search.strip():
    filtered = [
        i
        for i in filtered
        if rq_search.lower() in str(i["field"]).lower()
        or rq_search.lower() in str(i["value"]).lower()
        or rq_search.lower() in str(i["source"]).lower()
    ]

# ── Priority Sections ─────────────────────────────────
priority_order: list[str] = ["critical", "suspicious", "low"]

if not filtered:
    _empty_state("Review queue is empty. ✅ All items have been processed.")
else:
    for pri in priority_order:
        group = [i for i in filtered if i["priority"] == pri]
        if not group:
            continue
        label_map = {
            "critical": "🔴 Critical",
            "suspicious": "🟡 Suspicious",
            "low": "⚪ Low Risk",
        }
        with st.expander(
            f"{label_map[pri]}  ({len(group)} items)",
            expanded=(pri == "critical"),
        ):
            for item in group:
                unique_key = f"{pri}_{str(item['field']).lower().replace(' ', '_')}"
                _render_review_item(item, unique_key)
