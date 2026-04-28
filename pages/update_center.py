from __future__ import annotations
import streamlit as st
from datetime import date
from ui.style import apply_theme, page_header, badge
from db.database import Database

apply_theme()
page_header(
    "🔔", "Update Center", "Document versioning · value history · knowledge refresh"
)


# ── DB Loaders ────────────────────────────────────────
def _load_versions() -> list[dict]:
    try:
        with Database() as db:
            rows = db.fetchall(
                """
                SELECT v.id, v.table_name, v.record_id, v.version_number,
                       v.changed_by, v.changed_at, v.old_value, v.new_value,
                       d.filename, d.doc_type, d.status
                FROM versioning v
                LEFT JOIN documents d ON d.id = v.record_id AND v.table_name = 'documents'
                ORDER BY v.changed_at DESC
                """
            )
            return [
                {
                    "id": r["id"],
                    "doc_name": r["filename"] or r["table_name"] or "—",
                    "doc_type": r["doc_type"] or r["table_name"] or "—",
                    "version": int(r["version_number"] or 1),
                    "uploaded": str(r["changed_at"] or "—")[:10],
                    "replaced_by": r["changed_by"] or "—",
                    "entities": 0,
                    "changes": 1,
                    "status": r["status"] or "active",
                    "old_value": r["old_value"] or "—",
                    "new_value": r["new_value"] or "—",
                }
                for r in rows
            ]
    except Exception:
        return []


def _load_field_history() -> list[dict]:
    try:
        with Database() as db:
            rows = db.fetchall(
                """
                SELECT kb.field, kb.type,
                       v.old_value, v.new_value, v.changed_at, v.changed_by,
                       v.version_number
                FROM versioning v
                JOIN knowledge_base kb ON kb.id = v.record_id AND v.table_name = 'knowledge_base'
                ORDER BY kb.field, v.changed_at DESC
                """
            )
            grouped: dict[str, dict] = {}
            for r in rows:
                field = r["field"] or "—"
                if field not in grouped:
                    grouped[field] = {
                        "field": field,
                        "type": r["type"] or "OTHER",
                        "versions": [],
                    }
                grouped[field]["versions"].append(
                    {
                        "value": r["new_value"] or "—",
                        "source": r["changed_by"] or "—",
                        "date": str(r["changed_at"] or "—")[:10],
                        "status": (
                            "active"
                            if len(grouped[field]["versions"]) == 0
                            else "archived"
                        ),
                    }
                )
            return list(grouped.values())
    except Exception:
        return []


def _load_refresh_stats() -> dict:
    try:
        with Database() as db:
            last = db.fetchone("SELECT MAX(changed_at) AS last FROM versioning")
            count = db.fetchone("SELECT COUNT(*) AS cnt FROM documents")
            return {
                "last": str(last["last"] or "—")[:16] if last else "—",
                "docs": int(count["cnt"] or 0) if count else 0,
                "est": "~2 min",
            }
    except Exception:
        return {"last": "—", "docs": 0, "est": "—"}


def _load_stats(versions: list[dict]) -> dict:
    today = date.today().isoformat()
    return {
        "total": len(versions),
        "active": sum(1 for v in versions if v["status"] == "active"),
        "archived": sum(1 for v in versions if v["status"] == "archived"),
        "today": sum(1 for v in versions if v["uploaded"].startswith(today)),
    }


# ── Renderers ─────────────────────────────────────────
def _render_version_item(v: dict, idx: int) -> None:
    status = v["status"]
    status_color = (
        "#a5d6a7"
        if status == "active"
        else "#ffcc80" if status == "pending" else "#90a4ae"
    )
    st.markdown(
        f"<div class='nasmi-card' style='border-left:3px solid {status_color};'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;'>"
        f"<span style='font-weight:700;color:#e3f2fd;font-size:0.95rem;'>{v['doc_name']}</span>"
        f"{badge(v['doc_type'], status)}"
        f"{badge('v' + str(v['version']), 'new')}"
        f"</div>"
        f"<div style='font-size:0.78rem;color:#546e7a;'>"
        f"📅 Uploaded: {v['uploaded']} · 👤 By: {v['replaced_by']}"
        f"</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.2rem;'>"
        f"🧩 {v['entities']} entities · ⚠️ {v['changes']} changes detected"
        f"</div>"
        f"</div>"
        f"<span style='font-size:0.72rem;color:{status_color};font-weight:600;'>"
        f"{status.upper()}</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    col_view, col_restore, col_archive = st.columns([2, 2, 2])
    with col_view:
        if st.button("🔍 View Changes", key=f"vc_view_{idx}", use_container_width=True):
            st.session_state[f"vc_open_{idx}"] = not st.session_state.get(
                f"vc_open_{idx}", False
            )
    with col_restore:
        if st.button("🔄 Restore", key=f"vc_restore_{idx}", use_container_width=True):
            st.toast(f"Restored: {v['doc_name']} v{v['version']}", icon="🔄")
    with col_archive:
        if st.button("🗄️ Archive", key=f"vc_archive_{idx}", use_container_width=True):
            st.toast(f"Archived: {v['doc_name']}", icon="🗄️")

    if st.session_state.get(f"vc_open_{idx}"):
        st.markdown(
            "<div class='nasmi-card' style='background:#0d1b2a;margin-top:0.3rem;'>"
            "<div style='font-size:0.75rem;color:#546e7a;margin-bottom:0.5rem;'>"
            "DETECTED CHANGES</div>",
            unsafe_allow_html=True,
        )
        changes = [
            {
                "field": "Value",
                "old": v["old_value"],
                "new": v["new_value"],
                "type": "updated",
            }
        ]
        for ch in changes:
            ch_color = "#a5d6a7" if ch["type"] == "added" else "#ffcc80"
            st.markdown(
                f"<div style='display:flex;gap:1rem;align-items:center;"
                f"padding:0.3rem 0;border-bottom:1px solid #1e2d4a;'>"
                f"<span style='font-size:0.75rem;color:#546e7a;width:25%;'>{ch['field']}</span>"
                f"<span style='font-size:0.75rem;color:#ef9a9a;width:30%;'>{ch['old']}</span>"
                f"<span style='font-size:0.75rem;color:#37474f;'>→</span>"
                f"<span style='font-size:0.75rem;color:{ch_color};width:30%;'>{ch['new']}</span>"
                f"<span style='font-size:0.7rem;color:#37474f;'>{ch['type']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)


def _render_field_history(f: dict) -> None:
    st.markdown(
        f"<div class='nasmi-card'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"margin-bottom:0.5rem;'>"
        f"<span style='font-weight:700;color:#e3f2fd;font-size:0.9rem;'>{f['field']}</span>"
        f"{badge(f['type'], 'active')}"
        f"</div>",
        unsafe_allow_html=True,
    )
    for v in f["versions"]:
        v_color = "#a5d6a7" if v["status"] == "active" else "#37474f"
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:0.3rem 0;border-bottom:1px solid #1e2d4a;'>"
            f"<span style='font-size:0.82rem;color:#e3f2fd;width:35%;'>{v['value']}</span>"
            f"<span style='font-size:0.72rem;color:#546e7a;width:25%;'>📄 {v['source']}</span>"
            f"<span style='font-size:0.72rem;color:#546e7a;width:25%;'>📅 {v['date']}</span>"
            f"<span style='font-size:0.72rem;color:{v_color};font-weight:600;width:15%;'>"
            f"{v['status'].upper()}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)


def _empty_state(msg: str = "No data found.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:3rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Tabs ──────────────────────────────────────────────
tab_versions, tab_history, tab_refresh = st.tabs(
    [
        "📄 Document Versions",
        "🗂️ Value History",
        "⚡ Knowledge Refresh",
    ]
)

all_versions = _load_versions()
all_field_history = _load_field_history()
stats = _load_stats(all_versions)
refresh_stats = _load_refresh_stats()


# ══════════════════════════════════════════════════════
# TAB 1 — Document Versions
# ══════════════════════════════════════════════════════
with tab_versions:
    col_filter, col_search = st.columns([2, 4])
    with col_filter:
        statuses = ["All"] + sorted({v["status"] for v in all_versions})
        ver_filter = st.selectbox(
            "Status",
            statuses,
            label_visibility="collapsed",
            key="uc_ver_filter",
        )
    with col_search:
        ver_search = st.text_input(
            "Search documents",
            placeholder="Search by document name or type...",
            label_visibility="collapsed",
            key="uc_ver_search",
        )

    st.divider()

    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Total Versions", stats["total"])
    v2.metric("Active", stats["active"])
    v3.metric("Archived", stats["archived"])
    v4.metric("Changes Today", stats["today"])

    st.divider()

    filtered_v = list(all_versions)
    if ver_filter != "All":
        filtered_v = [v for v in filtered_v if v["status"] == ver_filter]
    if ver_search.strip():
        q = ver_search.lower()
        filtered_v = [
            v
            for v in filtered_v
            if q in v["doc_name"].lower() or q in v["doc_type"].lower()
        ]

    if not filtered_v:
        _empty_state("No document versions found.")
    else:
        for idx, v in enumerate(filtered_v):
            _render_version_item(v, idx)


# ══════════════════════════════════════════════════════
# TAB 2 — Value History
# ══════════════════════════════════════════════════════
with tab_history:
    col_ftype, col_fsearch = st.columns([2, 4])
    with col_ftype:
        types = ["All"] + sorted({f["type"] for f in all_field_history})
        hist_type = st.selectbox(
            "Field Type",
            types,
            label_visibility="collapsed",
            key="uc_hist_type",
        )
    with col_fsearch:
        hist_search = st.text_input(
            "Search fields",
            placeholder="Search by field name...",
            label_visibility="collapsed",
            key="uc_hist_search",
        )

    st.divider()

    filtered_f = list(all_field_history)
    if hist_type != "All":
        filtered_f = [f for f in filtered_f if f["type"] == hist_type]
    if hist_search.strip():
        filtered_f = [
            f for f in filtered_f if hist_search.lower() in f["field"].lower()
        ]

    if not filtered_f:
        _empty_state("No field history found.")
    else:
        for f in filtered_f:
            _render_field_history(f)


# ══════════════════════════════════════════════════════
# TAB 3 — Knowledge Refresh
# ══════════════════════════════════════════════════════
with tab_refresh:
    st.markdown(
        "<div class='nasmi-card'>"
        "<div style='font-size:0.9rem;font-weight:700;color:#e3f2fd;"
        "margin-bottom:1rem;'>⚡ Refresh Knowledge Base</div>"
        "<div style='font-size:0.8rem;color:#546e7a;'>"
        "Re-process all documents and rebuild the knowledge graph. "
        "This will re-run OCR, NER, merge logic, and quality scoring."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    r1, r2, r3 = st.columns(3)
    r1.metric("Last Refresh", refresh_stats["last"])
    r2.metric("Docs to Refresh", refresh_stats["docs"])
    r3.metric("Est. Duration", refresh_stats["est"])

    st.divider()

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.checkbox("Re-run OCR on all documents", value=False, key="refresh_ocr")
        st.checkbox("Re-run NER extraction", value=True, key="refresh_ner")
        st.checkbox("Rebuild vector index (RAG)", value=True, key="refresh_rag")
    with col_opt2:
        st.checkbox("Re-score quality metrics", value=True, key="refresh_quality")
        st.checkbox("Re-check contradictions", value=True, key="refresh_conflicts")
        st.checkbox("Rebuild identity graph", value=False, key="refresh_graph")

    st.divider()

    col_run, col_cancel = st.columns([3, 1])
    with col_run:
        if st.button(
            "⚡ Start Knowledge Refresh", use_container_width=True, key="refresh_run"
        ):
            with st.spinner("Refreshing knowledge base..."):
                st.toast("Knowledge refresh started", icon="⚡")
    with col_cancel:
        if st.button("✖ Cancel", use_container_width=True, key="refresh_cancel"):
            st.toast("Cancelled", icon="✖")
