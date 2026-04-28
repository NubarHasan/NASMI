from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import date
from ui.style import apply_theme, page_header, badge
from db.database import Database

apply_theme()
page_header("📋", "Logs", "System activity · audit trail · error tracking")


# ── DB Loaders ────────────────────────────────────────
def _load_activity() -> list[dict]:
    try:
        with Database() as db:
            rows = db.fetchall(
                """
                SELECT action, source_table, record_id, actor, new_value, created_at
                FROM audit_log
                ORDER BY created_at DESC
                LIMIT 500
                """
            )
            return [
                {
                    "timestamp": str(r["created_at"] or "—")[:19],
                    "level": _action_to_level(str(r["action"] or "")),
                    "module": str(r["source_table"] or "—").upper(),
                    "message": _format_message(r),
                    "action": str(r["action"] or "—").upper(),
                    "field": str(r["source_table"] or "—"),
                    "old": "—",
                    "new": str(r["new_value"] or "—"),
                    "source": str(r["actor"] or "—"),
                    "record_id": r["record_id"],
                }
                for r in rows
            ]
    except Exception:
        return []


def _action_to_level(action: str) -> str:
    action = action.lower()
    if "error" in action or "fail" in action or "reject" in action:
        return "ERROR"
    if "skip" in action or "warn" in action or "manual" in action:
        return "WARNING"
    if "accept" in action or "keep" in action or "save" in action:
        return "SUCCESS"
    return "INFO"


def _format_message(r: dict) -> str:
    action = str(r["action"] or "").upper()
    table = str(r["source_table"] or "")
    val = str(r["new_value"] or "")
    actor = str(r["actor"] or "system")
    return f'{action} on {table} (id={r["record_id"]}) by {actor}' + (
        f" → {val[:40]}" if val and val != "None" else ""
    )


def _load_audit() -> list[dict]:
    return _load_activity()


def _load_stats(rows: list[dict]) -> dict:
    today = date.today().isoformat()
    return {
        "total": len(rows),
        "errors": sum(1 for r in rows if r["level"] == "ERROR"),
        "warnings": sum(1 for r in rows if r["level"] == "WARNING"),
        "last": rows[0]["timestamp"][:16] if rows else "—",
        "today": sum(1 for r in rows if r["timestamp"].startswith(today)),
        "critical": sum(1 for r in rows if r["level"] == "ERROR"),
    }


# ── Renderers ─────────────────────────────────────────
def _render_log_row(log: dict) -> None:
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


def _empty_state(msg: str = "No logs found.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:3rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Tabs ──────────────────────────────────────────────
tab_activity, tab_audit = st.tabs(["📡 Activity Log", "🔏 Audit Trail"])

all_rows = _load_activity()
stats = _load_stats(all_rows)

# ══════════════════════════════════════════════════════
# TAB 1 — Activity Log
# ══════════════════════════════════════════════════════
with tab_activity:
    col_level, col_module, col_search, col_export = st.columns([2, 2, 3, 1])

    with col_level:
        level_filter = st.selectbox(
            "Level",
            ["All", "INFO", "SUCCESS", "WARNING", "ERROR"],
            label_visibility="collapsed",
            key="log_level",
        )
    with col_module:
        modules = ["All"] + sorted(
            {r["module"] for r in all_rows if r["module"] != "—"}
        )
        module_filter = st.selectbox(
            "Module",
            modules,
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
    with col_export:
        export_btn = st.button("⬇️", use_container_width=True, key="export_logs")

    st.divider()

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Total Entries", stats["total"])
    a2.metric("Errors", stats["errors"])
    a3.metric("Warnings", stats["warnings"])
    a4.metric("Last Activity", stats["last"])

    st.divider()

    filtered_logs = list(all_rows)
    if level_filter != "All":
        filtered_logs = [r for r in filtered_logs if r["level"] == level_filter]
    if module_filter != "All":
        filtered_logs = [r for r in filtered_logs if r["module"] == module_filter]
    if log_search.strip():
        q = log_search.lower()
        filtered_logs = [
            r
            for r in filtered_logs
            if q in r["message"].lower() or q in r["module"].lower()
        ]

    if export_btn and filtered_logs:
        csv = pd.DataFrame(filtered_logs)[
            ["timestamp", "level", "module", "message"]
        ].to_csv(index=False)
        st.download_button(
            "📥 Download CSV", csv, "activity_log.csv", "text/csv", key="dl_activity"
        )

    st.markdown(
        "<div class='nasmi-card' style='padding:0.5rem 1rem;'>"
        "<div style='display:flex;gap:0.8rem;padding:0.3rem 0;"
        "border-bottom:2px solid #1e2d4a;margin-bottom:0.3rem;'>"
        "<span style='font-size:0.7rem;color:#37474f;font-weight:700;width:130px;flex-shrink:0;'>TIMESTAMP</span>"
        "<span style='font-size:0.7rem;color:#37474f;font-weight:700;width:75px;flex-shrink:0;'>LEVEL</span>"
        "<span style='font-size:0.7rem;color:#37474f;font-weight:700;width:110px;flex-shrink:0;'>MODULE</span>"
        "<span style='font-size:0.7rem;color:#37474f;font-weight:700;'>MESSAGE</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    if not filtered_logs:
        _empty_state("No log entries match the current filters.")
    else:
        for log in filtered_logs:
            _render_log_row(log)

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# TAB 2 — Audit Trail
# ══════════════════════════════════════════════════════
with tab_audit:
    col_afilter, col_asearch, col_aexport = st.columns([2, 4, 1])

    with col_afilter:
        audit_filter = st.selectbox(
            "Action",
            ["All"] + sorted({r["action"] for r in all_rows}),
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
    with col_aexport:
        audit_export_btn = st.button("⬇️", use_container_width=True, key="export_audit")

    st.divider()

    au1, au2, au3 = st.columns(3)
    au1.metric("Total Actions", stats["total"])
    au2.metric("Today", stats["today"])
    au3.metric("Critical", stats["critical"])

    st.divider()

    filtered_a = list(all_rows)
    if audit_filter != "All":
        filtered_a = [r for r in filtered_a if r["action"] == audit_filter]
    if audit_search.strip():
        q = audit_search.lower()
        filtered_a = [
            r
            for r in filtered_a
            if q in r["field"].lower()
            or q in r["action"].lower()
            or q in r["message"].lower()
        ]

    if audit_export_btn and filtered_a:
        csv = pd.DataFrame(filtered_a)[
            ["timestamp", "action", "field", "old", "new", "source"]
        ].to_csv(index=False)
        st.download_button(
            "📥 Download CSV", csv, "audit_trail.csv", "text/csv", key="dl_audit"
        )

    action_color_map: dict[str, str] = {
        "CREATE": "#a5d6a7",
        "UPDATE": "#ffcc80",
        "DELETE": "#ef9a9a",
        "EXPORT": "#90caf9",
        "LOGIN": "#ce93d8",
        "ACCEPT": "#a5d6a7",
        "REJECT": "#ef9a9a",
        "SKIP": "#90a4ae",
        "MANUAL": "#ffcc80",
    }

    st.markdown(
        "<div class='nasmi-card' style='padding:0.5rem 1rem;'>",
        unsafe_allow_html=True,
    )

    if not filtered_a:
        _empty_state("No audit entries found.")
    else:
        for r in filtered_a:
            color = action_color_map.get(r["action"], "#90a4ae")
            st.markdown(
                f"<div style='display:flex;align-items:flex-start;gap:0.8rem;"
                f"padding:0.5rem 0;border-bottom:1px solid #1e2d4a;'>"
                f"<span style='font-size:0.72rem;color:#37474f;width:130px;flex-shrink:0;'>{r['timestamp']}</span>"
                f"<span style='font-size:0.72rem;color:{color};font-weight:700;width:80px;flex-shrink:0;'>{r['action']}</span>"
                f"<span style='font-size:0.75rem;color:#e3f2fd;width:120px;flex-shrink:0;'>{r['field']}</span>"
                f"<span style='font-size:0.72rem;color:#ef9a9a;width:80px;flex-shrink:0;'>{r['old']}</span>"
                f"<span style='font-size:0.72rem;color:#37474f;'>→</span>"
                f"<span style='font-size:0.72rem;color:#a5d6a7;width:80px;flex-shrink:0;'>{r['new'][:30] if r['new'] != '—' else '—'}</span>"
                f"<span style='font-size:0.72rem;color:#546e7a;'>{r['source']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)
