from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header(
    "⚠️",
    "Contradictions",
    "Detected conflicts between extracted values — review and resolve",
)


# ── Renderers ─────────────────────────────────────────
def _render_conflict(c: dict[str, object]) -> None:
    severity = str(c["severity"])
    severity_color = (
        "#ef9a9a"
        if severity == "high"
        else "#ffcc80" if severity == "medium" else "#90a4ae"
    )
    st.markdown(
        f"<div class='nasmi-card' style='border-left:3px solid {severity_color};'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;'>"
        f"<span style='font-weight:700;color:#e3f2fd;font-size:0.95rem;'>{c['field']}</span>"
        f"{badge(severity.upper(), 'conflict')}"
        f"{badge(str(c['status']), str(c['status']))}"
        f"</div>"
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;margin-top:0.3rem;'>"
        f"<div style='background:#0d1b2a;border-radius:6px;padding:0.6rem;'>"
        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;margin-bottom:0.2rem;'>Value A</div>"
        f"<div style='font-size:0.9rem;font-weight:600;color:#e3f2fd;'>{c['value_a']}</div>"
        f"<div style='font-size:0.7rem;color:#37474f;margin-top:0.2rem;'>"
        f"📄 {c['source_a']} · 📅 {c['date_a']}</div>"
        f"</div>"
        f"<div style='background:#0d1b2a;border-radius:6px;padding:0.6rem;'>"
        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;margin-bottom:0.2rem;'>Value B</div>"
        f"<div style='font-size:0.9rem;font-weight:600;color:#e3f2fd;'>{c['value_b']}</div>"
        f"<div style='font-size:0.7rem;color:#37474f;margin-top:0.2rem;'>"
        f"📄 {c['source_b']} · 📅 {c['date_b']}</div>"
        f"</div>"
        f"</div>"
        f"<div style='font-size:0.75rem;color:#546e7a;margin-top:0.5rem;'>"
        f"🔍 {c['note']}"
        f"</div>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_resolve_actions(c: dict[str, object], idx: int) -> None:
    col_a, col_b, col_skip, col_manual = st.columns([2, 2, 1, 2])
    with col_a:
        if st.button(f"✅ Keep A", key=f"keep_a_{idx}", use_container_width=True):
            st.toast(f"Kept Value A for {c['field']}", icon="✅")
    with col_b:
        if st.button(f"✅ Keep B", key=f"keep_b_{idx}", use_container_width=True):
            st.toast(f"Kept Value B for {c['field']}", icon="✅")
    with col_skip:
        if st.button("⏭", key=f"skip_{idx}", use_container_width=True):
            st.toast("Skipped", icon="⏭")
    with col_manual:
        if st.button("✏️ Enter Manually", key=f"manual_{idx}", use_container_width=True):
            st.session_state[f"manual_open_{idx}"] = True

    if st.session_state.get(f"manual_open_{idx}"):
        manual_val = st.text_input(
            "Manual value",
            placeholder=f"Enter correct value for {c['field']}...",
            key=f"manual_val_{idx}",
        )
        if st.button("💾 Save", key=f"save_manual_{idx}"):
            if manual_val.strip():
                st.toast(f"Saved: {manual_val}", icon="💾")
                st.session_state[f"manual_open_{idx}"] = False
            else:
                st.warning("Value cannot be empty.")


def _empty_state(msg: str = "No conflicts found.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:3rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Controls ──────────────────────────────────────────
col_sev, col_status, col_search = st.columns([2, 2, 4])

with col_sev:
    sev_filter = st.selectbox(
        "Severity",
        ["All", "high", "medium", "low"],
        label_visibility="collapsed",
        key="con_sev",
    )

with col_status:
    status_filter = st.selectbox(
        "Status",
        ["All", "unresolved", "resolved", "skipped"],
        label_visibility="collapsed",
        key="con_status",
    )

with col_search:
    con_search = st.text_input(
        "Search conflicts",
        placeholder="Search by field, source, value...",
        label_visibility="collapsed",
        key="con_search",
    )

st.divider()

# ── Stats ─────────────────────────────────────────────
s1, s2, s3, s4 = st.columns(4)
s1.metric("Total Conflicts", "—")
s2.metric("High Severity", "—")
s3.metric("Unresolved", "—")
s4.metric("Resolved", "—")

st.divider()

# ── Mock Conflicts ────────────────────────────────────
mock_conflicts: list[dict[str, object]] = [
    {
        "field": "IBAN",
        "value_a": "—",
        "source_a": "—",
        "date_a": "—",
        "value_b": "—",
        "source_b": "—",
        "date_b": "—",
        "severity": "high",
        "status": "unresolved",
        "note": "Two different IBAN values found across documents.",
    },
    {
        "field": "Address",
        "value_a": "—",
        "source_a": "—",
        "date_a": "—",
        "value_b": "—",
        "source_b": "—",
        "date_b": "—",
        "severity": "medium",
        "status": "unresolved",
        "note": "Address mismatch between Meldebescheinigung and Personalausweis.",
    },
    {
        "field": "Date of Birth",
        "value_a": "—",
        "source_a": "—",
        "date_a": "—",
        "value_b": "—",
        "source_b": "—",
        "date_b": "—",
        "severity": "high",
        "status": "unresolved",
        "note": "Date of birth differs between passport and ID card.",
    },
    {
        "field": "Phone Number",
        "value_a": "—",
        "source_a": "—",
        "date_a": "—",
        "value_b": "—",
        "source_b": "—",
        "date_b": "—",
        "severity": "low",
        "status": "skipped",
        "note": "Minor format difference — may be same number.",
    },
]

# ── Filter Logic ──────────────────────────────────────
filtered: list[dict[str, object]] = list(mock_conflicts)

if sev_filter != "All":
    filtered = [c for c in filtered if c["severity"] == sev_filter]

if status_filter != "All":
    filtered = [c for c in filtered if c["status"] == status_filter]

if con_search.strip():
    filtered = [
        c
        for c in filtered
        if con_search.lower() in str(c["field"]).lower()
        or con_search.lower() in str(c["value_a"]).lower()
        or con_search.lower() in str(c["value_b"]).lower()
        or con_search.lower() in str(c["source_a"]).lower()
        or con_search.lower() in str(c["source_b"]).lower()
    ]

# ── Render ────────────────────────────────────────────
if not filtered:
    _empty_state("No conflicts match the current filter. ✅")
else:
    for idx, c in enumerate(filtered):
        _render_conflict(c)
        _render_resolve_actions(c, idx)
        st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
