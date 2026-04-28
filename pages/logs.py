from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header("📋", "Logs", "System activity · audit trail · error tracking")


# ── Renderers ─────────────────────────────────────────
def _render_log_row(log: dict[str, object]) -> None:
    level = str(log["level"])
    level_color = (
        "#ef9a9a"
        if level == "ERROR"
        else (
            "#ffcc80"
            if level == "WARNING"
            else "#a5d6a7" if level == "SUCCESS" else "#90a4ae"
        )
    )
    level_icon = (
        "🔴"
        if level == "ERROR"
        else "🟡" if level == "WARNING" else "🟢" if level == "SUCCESS" else "⚪"
    )
    st.markdown(
        f"<div style='display:flex;align-items:flex-start;gap:0.8rem;"
        f"padding:0.5rem 0;border-bottom:1px solid #1e2d4a;'>"
        f"<span style='font-size:0.75rem;color:#37474f;width:130px;flex-shrink:0;'>"
        f"{log['timestamp']}</span>"
        f"<span style='font-size:0.72rem;color:{level_color};font-weight:700;"
        f"width:75px;flex-shrink:0;'>{level_icon} {level}</span>"
        f"<span style='font-size:0.72rem;color:#546e7a;width:110px;flex-shrink:0;'>"
        f"{log['module']}</span>"
        f"<span style='font-size:0.78rem;color:#e3f2fd;flex:1;'>{log['message']}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_error_card(err: dict[str, object], idx: int) -> None:
    st.markdown(
        f"<div class='nasmi-card' style='border-left:3px solid #ef9a9a;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;'>"
        f"<span style='font-weight:700;color:#ef9a9a;font-size:0.92rem;'>{err['title']}</span>"
        f"{badge(str(err['module']), 'conflict')}"
        f"</div>"
        f"<div style='font-size:0.78rem;color:#546e7a;'>"
        f"📅 {err['timestamp']} · 🔁 {err['count']}x occurrences"
        f"</div>"
        f"<div style='font-size:0.75rem;color:#37474f;margin-top:0.3rem;font-family:monospace;'>"
        f"{err['trace']}"
        f"</div>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    col_resolve, col_ignore = st.columns([3, 1])
    with col_resolve:
        if st.button(
            "✅ Mark Resolved", key=f"err_resolve_{idx}", use_container_width=True
        ):
            st.toast(f"Resolved: {err['title']}", icon="✅")
    with col_ignore:
        if st.button("🚫 Ignore", key=f"err_ignore_{idx}", use_container_width=True):
            st.toast("Ignored", icon="🚫")
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)


def _empty_state(msg: str = "No logs found.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:3rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Tabs ──────────────────────────────────────────────
tab_activity, tab_errors, tab_audit = st.tabs(
    [
        "📡 Activity Log",
        "🔴 Errors & Warnings",
        "🔏 Audit Trail",
    ]
)


# ══════════════════════════════════════════════════════
# TAB 1 — Activity Log
# ══════════════════════════════════════════════════════
with tab_activity:
    col_level, col_module, col_search, col_clear = st.columns([2, 2, 3, 1])

    with col_level:
        level_filter = st.selectbox(
            "Level",
            ["All", "INFO", "SUCCESS", "WARNING", "ERROR"],
            label_visibility="collapsed",
            key="log_level",
        )
    with col_module:
        module_filter = st.selectbox(
            "Module",
            ["All", "OCR", "NER", "DB", "UI", "AI", "Export", "Auth"],
            label_visibility="collapsed",
            key="log_module",
        )
    with col_search:
        log_search = st.text_input(
            "Search logs",
            placeholder="Search by message or module...",
            label_visibility="collapsed",
            key="log_search",
        )
    with col_clear:
        if st.button("🗑 Clear", use_container_width=True, key="clear_logs"):
            st.toast("Logs cleared", icon="🗑")

    st.divider()

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Total Entries", "—")
    a2.metric("Errors", "—")
    a3.metric("Warnings", "—")
    a4.metric("Last Activity", "—")

    st.divider()

    st.markdown(
        "<div class='nasmi-card' style='padding:0.5rem 1rem;'>"
        "<div style='display:flex;gap:0.8rem;padding:0.3rem 0;"
        "border-bottom:2px solid #1e2d4a;margin-bottom:0.3rem;'>"
        "<span style='font-size:0.7rem;color:#37474f;font-weight:700;"
        "width:130px;flex-shrink:0;'>TIMESTAMP</span>"
        "<span style='font-size:0.7rem;color:#37474f;font-weight:700;"
        "width:75px;flex-shrink:0;'>LEVEL</span>"
        "<span style='font-size:0.7rem;color:#37474f;font-weight:700;"
        "width:110px;flex-shrink:0;'>MODULE</span>"
        "<span style='font-size:0.7rem;color:#37474f;font-weight:700;'>MESSAGE</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    mock_logs: list[dict[str, object]] = [
        {
            "timestamp": "—",
            "level": "SUCCESS",
            "module": "OCR",
            "message": "Document processed successfully.",
        },
        {
            "timestamp": "—",
            "level": "INFO",
            "module": "NER",
            "message": "Entity extraction completed.",
        },
        {
            "timestamp": "—",
            "level": "WARNING",
            "module": "DB",
            "message": "Duplicate key detected — skipped.",
        },
        {
            "timestamp": "—",
            "level": "ERROR",
            "module": "AI",
            "message": "Model response timeout — retrying.",
        },
        {
            "timestamp": "—",
            "level": "INFO",
            "module": "Export",
            "message": "PDF certificate generated.",
        },
        {
            "timestamp": "—",
            "level": "SUCCESS",
            "module": "Auth",
            "message": "User session started.",
        },
        {
            "timestamp": "—",
            "level": "WARNING",
            "module": "OCR",
            "message": "Low confidence score detected.",
        },
        {
            "timestamp": "—",
            "level": "INFO",
            "module": "UI",
            "message": "Page loaded: Knowledge Base.",
        },
    ]

    filtered_logs: list[dict[str, object]] = list(mock_logs)

    if level_filter != "All":
        filtered_logs = [l for l in filtered_logs if l["level"] == level_filter]
    if module_filter != "All":
        filtered_logs = [l for l in filtered_logs if l["module"] == module_filter]
    if log_search.strip():
        filtered_logs = [
            l
            for l in filtered_logs
            if log_search.lower() in str(l["message"]).lower()
            or log_search.lower() in str(l["module"]).lower()
        ]

    if not filtered_logs:
        _empty_state("No log entries match the current filters.")
    else:
        for log in filtered_logs:
            _render_log_row(log)

    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    if st.button("⬇️ Export Logs as CSV", use_container_width=True, key="export_logs"):
        st.toast("Logs exported as CSV", icon="⬇️")


# ══════════════════════════════════════════════════════
# TAB 2 — Errors & Warnings
# ══════════════════════════════════════════════════════
with tab_errors:
    col_efilter, col_esearch = st.columns([2, 4])
    with col_efilter:
        err_filter = st.selectbox(
            "Filter",
            ["All", "ERROR", "WARNING"],
            label_visibility="collapsed",
            key="err_filter",
        )
    with col_esearch:
        err_search = st.text_input(
            "Search errors",
            placeholder="Search by title or module...",
            label_visibility="collapsed",
            key="err_search",
        )

    st.divider()

    e1, e2, e3 = st.columns(3)
    e1.metric("Active Errors", "—")
    e2.metric("Warnings", "—")
    e3.metric("Resolved Today", "—")

    st.divider()

    mock_errors: list[dict[str, object]] = [
        {
            "title": "Model Response Timeout",
            "module": "AI",
            "timestamp": "—",
            "count": 3,
            "level": "ERROR",
            "trace": "TimeoutError: Ollama model did not respond within 30s.",
        },
        {
            "title": "Low OCR Confidence",
            "module": "OCR",
            "timestamp": "—",
            "count": 5,
            "level": "WARNING",
            "trace": "ConfidenceWarning: Score below threshold (0.45 < 0.70).",
        },
        {
            "title": "DB Duplicate Key",
            "module": "DB",
            "timestamp": "—",
            "count": 1,
            "level": "WARNING",
            "trace": 'IntegrityError: Duplicate entry for field "iban" in table "knowledge".',
        },
    ]

    filtered_e: list[dict[str, object]] = list(mock_errors)
    if err_filter != "All":
        filtered_e = [e for e in filtered_e if e["level"] == err_filter]
    if err_search.strip():
        filtered_e = [
            e
            for e in filtered_e
            if err_search.lower() in str(e["title"]).lower()
            or err_search.lower() in str(e["module"]).lower()
        ]

    if not filtered_e:
        _empty_state("No errors or warnings. ✅ System is healthy.")
    else:
        for idx, err in enumerate(filtered_e):
            _render_error_card(err, idx)


# ══════════════════════════════════════════════════════
# TAB 3 — Audit Trail
# ══════════════════════════════════════════════════════
with tab_audit:
    col_afilter, col_asearch = st.columns([2, 4])
    with col_afilter:
        audit_filter = st.selectbox(
            "Action",
            ["All", "CREATE", "UPDATE", "DELETE", "EXPORT", "LOGIN"],
            label_visibility="collapsed",
            key="audit_filter",
        )
    with col_asearch:
        audit_search = st.text_input(
            "Search audit trail",
            placeholder="Search by action or field...",
            label_visibility="collapsed",
            key="audit_search",
        )

    st.divider()

    au1, au2, au3 = st.columns(3)
    au1.metric("Total Actions", "—")
    au2.metric("Today", "—")
    au3.metric("Critical", "—")

    st.divider()

    st.markdown(
        "<div class='nasmi-card' style='padding:0.5rem 1rem;'>",
        unsafe_allow_html=True,
    )

    mock_audit: list[dict[str, object]] = [
        {
            "timestamp": "—",
            "action": "CREATE",
            "field": "Full Name",
            "old": "—",
            "new": "—",
            "source": "Personalausweis",
        },
        {
            "timestamp": "—",
            "action": "UPDATE",
            "field": "Address",
            "old": "—",
            "new": "—",
            "source": "Meldebescheinigung",
        },
        {
            "timestamp": "—",
            "action": "DELETE",
            "field": "Phone",
            "old": "—",
            "new": "—",
            "source": "Manual",
        },
        {
            "timestamp": "—",
            "action": "EXPORT",
            "field": "Identity",
            "old": "—",
            "new": "—",
            "source": "Export Page",
        },
        {
            "timestamp": "—",
            "action": "LOGIN",
            "field": "Session",
            "old": "—",
            "new": "—",
            "source": "Auth",
        },
    ]

    filtered_a: list[dict[str, object]] = list(mock_audit)
    if audit_filter != "All":
        filtered_a = [a for a in filtered_a if a["action"] == audit_filter]
    if audit_search.strip():
        filtered_a = [
            a
            for a in filtered_a
            if audit_search.lower() in str(a["field"]).lower()
            or audit_search.lower() in str(a["action"]).lower()
        ]

    action_color_map: dict[str, str] = {
        "CREATE": "#a5d6a7",
        "UPDATE": "#ffcc80",
        "DELETE": "#ef9a9a",
        "EXPORT": "#90caf9",
        "LOGIN": "#ce93d8",
    }

    if not filtered_a:
        _empty_state("No audit entries found.")
    else:
        for a in filtered_a:
            color = action_color_map.get(str(a["action"]), "#90a4ae")
            st.markdown(
                f"<div style='display:flex;align-items:flex-start;gap:0.8rem;"
                f"padding:0.5rem 0;border-bottom:1px solid #1e2d4a;'>"
                f"<span style='font-size:0.72rem;color:#37474f;width:130px;flex-shrink:0;'>"
                f"{a['timestamp']}</span>"
                f"<span style='font-size:0.72rem;color:{color};font-weight:700;"
                f"width:70px;flex-shrink:0;'>{a['action']}</span>"
                f"<span style='font-size:0.75rem;color:#e3f2fd;width:120px;flex-shrink:0;'>"
                f"{a['field']}</span>"
                f"<span style='font-size:0.72rem;color:#ef9a9a;width:80px;flex-shrink:0;'>"
                f"{a['old']}</span>"
                f"<span style='font-size:0.72rem;color:#37474f;'>→</span>"
                f"<span style='font-size:0.72rem;color:#a5d6a7;width:80px;flex-shrink:0;'>"
                f"{a['new']}</span>"
                f"<span style='font-size:0.72rem;color:#546e7a;'>{a['source']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    if st.button(
        "⬇️ Export Audit Trail as CSV", use_container_width=True, key="export_audit"
    ):
        st.toast("Audit trail exported as CSV", icon="⬇️")
