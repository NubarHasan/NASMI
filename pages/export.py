import streamlit as st
from ui.style import apply_theme, page_header, badge
from db.database import Database

apply_theme()
page_header("📤", "Export", "Export documents · data · reports · certificates")


# ── Renderers ─────────────────────────────────────────
def _render_export_card(
    title: str,
    desc: str,
    icon: str,
    key: str,
    tag: str = "",
    tag_status: str = "active",
) -> None:
    st.markdown(
        f"<div class='nasmi-card'>"
        f"<div style='display:flex;align-items:flex-start;gap:0.8rem;'>"
        f"<div style='font-size:2rem;'>{icon}</div>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;'>"
        f"<span style='font-weight:700;color:#e3f2fd;font-size:0.95rem;'>{title}</span>"
        f"{badge(tag, tag_status) if tag else ''}"
        f"</div>"
        f"<div style='font-size:0.78rem;color:#546e7a;'>{desc}</div>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button(f"📤 Export {title}", key=key, use_container_width=True):
        st.session_state[f"export_open_{key}"] = not st.session_state.get(
            f"export_open_{key}", False
        )


def _render_format_selector(key: str) -> str:
    return str(
        st.selectbox(
            "Format",
            ["PDF", "JSON", "CSV", "Excel"],
            key=f"fmt_{key}",
            label_visibility="collapsed",
        )
    )


def _empty_state(msg: str = "No exports yet.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:3rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Tabs ──────────────────────────────────────────────
tab_quick, tab_custom, tab_history = st.tabs(
    [
        "⚡ Quick Export",
        "🛠️ Custom Export",
        "🗂️ Export History",
    ]
)


# ══════════════════════════════════════════════════════
# TAB 1 — Quick Export
# ══════════════════════════════════════════════════════
with tab_quick:
    st.markdown(
        "<div style='font-size:0.8rem;color:#546e7a;margin-bottom:1rem;'>"
        "One-click exports for the most common use cases.</div>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)

    with col_a:
        _render_export_card(
            "Identity Summary",
            "Core identity fields + trust score in a single document.",
            "🪪",
            "quick_identity",
            "PDF",
            "active",
        )
        if st.session_state.get("export_open_quick_identity"):
            fmt = _render_format_selector("quick_identity")
            if st.button(
                "✅ Confirm Export",
                key="confirm_quick_identity",
                use_container_width=True,
            ):
                st.toast(f"Identity Summary exported as {fmt}", icon="📤")
                st.session_state["export_open_quick_identity"] = False

        _render_export_card(
            "Knowledge Base",
            "All extracted entities and values across all documents.",
            "🧠",
            "quick_kb",
            "JSON / CSV",
            "active",
        )
        if st.session_state.get("export_open_quick_kb"):
            fmt = _render_format_selector("quick_kb")
            if st.button(
                "✅ Confirm Export", key="confirm_quick_kb", use_container_width=True
            ):
                st.toast(f"Knowledge Base exported as {fmt}", icon="📤")
                st.session_state["export_open_quick_kb"] = False

        _render_export_card(
            "Timeline Report",
            "Chronological history of all life events and documents.",
            "📅",
            "quick_timeline",
            "PDF",
            "active",
        )
        if st.session_state.get("export_open_quick_timeline"):
            fmt = _render_format_selector("quick_timeline")
            if st.button(
                "✅ Confirm Export",
                key="confirm_quick_timeline",
                use_container_width=True,
            ):
                st.toast(f"Timeline Report exported as {fmt}", icon="📤")
                st.session_state["export_open_quick_timeline"] = False

    with col_b:
        _render_export_card(
            "Conflict Report",
            "All detected contradictions and their resolution status.",
            "⚠️",
            "quick_conflicts",
            "PDF / JSON",
            "conflict",
        )
        if st.session_state.get("export_open_quick_conflicts"):
            fmt = _render_format_selector("quick_conflicts")
            if st.button(
                "✅ Confirm Export",
                key="confirm_quick_conflicts",
                use_container_width=True,
            ):
                st.toast(f"Conflict Report exported as {fmt}", icon="📤")
                st.session_state["export_open_quick_conflicts"] = False

        _render_export_card(
            "All Documents",
            "Download all uploaded documents as a ZIP archive.",
            "📦",
            "quick_docs",
            "ZIP",
            "active",
        )
        if st.session_state.get("export_open_quick_docs"):
            st.markdown(
                "<div style='font-size:0.78rem;color:#546e7a;padding:0.3rem 0;'>"
                "All documents will be packaged as a ZIP file.</div>",
                unsafe_allow_html=True,
            )
            if st.button(
                "✅ Confirm Export", key="confirm_quick_docs", use_container_width=True
            ):
                st.toast("Documents exported as ZIP", icon="📦")
                st.session_state["export_open_quick_docs"] = False

        _render_export_card(
            "Audit Log",
            "Full system activity log with timestamps and actions.",
            "📋",
            "quick_audit",
            "CSV",
            "pending",
        )
        if st.session_state.get("export_open_quick_audit"):
            fmt = _render_format_selector("quick_audit")
            if st.button(
                "✅ Confirm Export", key="confirm_quick_audit", use_container_width=True
            ):
                st.toast(f"Audit Log exported as {fmt}", icon="📤")
                st.session_state["export_open_quick_audit"] = False


# ══════════════════════════════════════════════════════
# TAB 2 — Custom Export
# ══════════════════════════════════════════════════════
with tab_custom:
    st.markdown(
        "<div style='font-size:0.8rem;color:#546e7a;margin-bottom:1rem;'>"
        "Build a custom export by selecting exactly what to include.</div>",
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown(
            "<div class='nasmi-card'>"
            "<div style='font-size:0.85rem;font-weight:700;color:#e3f2fd;"
            "margin-bottom:0.8rem;'>📋 Select Content</div>",
            unsafe_allow_html=True,
        )
        inc_identity = st.checkbox("🪪 Identity Core", value=True, key="cust_identity")
        inc_kb = st.checkbox("🧠 Knowledge Base", value=True, key="cust_kb")
        inc_docs = st.checkbox("📄 Documents (ZIP)", value=False, key="cust_docs")
        inc_timeline = st.checkbox("📅 Timeline", value=False, key="cust_timeline")
        inc_conflicts = st.checkbox(
            "⚠️ Conflict Report", value=False, key="cust_conflicts"
        )
        inc_claims = st.checkbox("📜 Signed Claims", value=False, key="cust_claims")
        inc_audit = st.checkbox("📋 Audit Log", value=False, key="cust_audit")
        st.markdown("</div>", unsafe_allow_html=True)

        if inc_kb:
            st.markdown(
                "<div class='nasmi-card' style='margin-top:0.5rem;'>"
                "<div style='font-size:0.82rem;font-weight:700;color:#e3f2fd;"
                "margin-bottom:0.5rem;'>🧩 Knowledge Base Fields</div>",
                unsafe_allow_html=True,
            )
            kb_fields = st.multiselect(
                "Fields",
                [
                    "Full Name",
                    "Date of Birth",
                    "Nationality",
                    "ID Number",
                    "Address",
                    "IBAN",
                    "Tax ID",
                    "Phone",
                    "Email",
                ],
                default=["Full Name", "Date of Birth", "Nationality"],
                key="cust_kb_fields",
                label_visibility="collapsed",
            )
            st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown(
            "<div class='nasmi-card'>"
            "<div style='font-size:0.85rem;font-weight:700;color:#e3f2fd;"
            "margin-bottom:0.8rem;'>⚙️ Export Options</div>",
            unsafe_allow_html=True,
        )
        cust_format = str(
            st.selectbox(
                "Format",
                ["PDF", "JSON", "CSV", "Excel", "ZIP (All)"],
                key="cust_format",
            )
        )
        cust_lang = str(
            st.selectbox("Language", ["English", "Deutsch", "العربية"], key="cust_lang")
        )
        st.checkbox("Include QR Code", value=True, key="cust_qr")
        st.checkbox("Include Timestamps", value=True, key="cust_ts")
        st.checkbox("Include Source Refs", value=False, key="cust_src")
        st.checkbox("Password Protect PDF", value=False, key="cust_pwd")
        st.markdown("</div>", unsafe_allow_html=True)

        selected = sum(
            [
                inc_identity,
                inc_kb,
                inc_docs,
                inc_timeline,
                inc_conflicts,
                inc_claims,
                inc_audit,
            ]
        )
        st.markdown(
            f"<div class='nasmi-card' style='margin-top:0.5rem;'>"
            f"<div style='font-size:0.85rem;font-weight:700;color:#e3f2fd;margin-bottom:0.5rem;'>📊 Export Summary</div>"
            f"<div style='font-size:0.78rem;color:#546e7a;'>"
            f"✅ {selected} section(s) selected · Format: {cust_format}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    col_gen, col_preview = st.columns([3, 1])
    with col_gen:
        if st.button("📤 Generate Custom Export", use_container_width=True):
            if selected > 0:
                with st.spinner("Building export package..."):
                    st.toast(f"Custom export ready ({cust_format})", icon="📤")
            else:
                st.warning("Select at least one section.")
    with col_preview:
        if st.button("👁 Preview", use_container_width=True):
            st.toast("Preview coming soon", icon="👁")


# ══════════════════════════════════════════════════════
# TAB 3 — Export History (DB-connected)
# ══════════════════════════════════════════════════════
with tab_history:
    col_hfilter, col_hsearch = st.columns([2, 4])
    with col_hfilter:
        hist_filter = str(
            st.selectbox(
                "Type",
                ["All", "Identity", "Knowledge Base", "Documents", "Custom"],
                label_visibility="collapsed",
                key="exp_hist_filter",
            )
        )
    with col_hsearch:
        hist_search = str(
            st.text_input(
                "Search history",
                placeholder="Search by export name...",
                label_visibility="collapsed",
                key="exp_hist_search",
            )
        )

    st.divider()

    with Database() as db:
        total_exports = db.fetchone(
            "SELECT COUNT(*) as cnt FROM audit_log WHERE action LIKE ?", ("%export%",)
        )
        week_exports = db.fetchone(
            "SELECT COUNT(*) as cnt FROM audit_log WHERE action LIKE ? AND created_at >= date('now', '-7 days')",
            ("%export%",),
        )
        history_rows = db.fetchall(
            "SELECT action, details, created_at FROM audit_log WHERE action LIKE ? ORDER BY created_at DESC LIMIT 50",
            ("%export%",),
        )

    total_count = int(total_exports["cnt"]) if total_exports else 0
    week_count = int(week_exports["cnt"]) if week_exports else 0

    h1, h2, h3 = st.columns(3)
    h1.metric("Total Exports", str(total_count))
    h2.metric("This Week", str(week_count))
    h3.metric("Storage Used", "—")

    st.divider()

    history: list[dict[str, str]] = []
    for r in history_rows:
        history.append(
            {
                "name": str(r["action"] or "—"),
                "type": str(r["details"] or "Custom"),
                "format": "—",
                "date": str(r["created_at"] or "—"),
                "size": "—",
            }
        )

    filtered_h = list(history)
    if hist_filter != "All":
        filtered_h = [h for h in filtered_h if hist_filter.lower() in h["type"].lower()]
    if hist_search.strip():
        filtered_h = [h for h in filtered_h if hist_search.lower() in h["name"].lower()]

    if not filtered_h:
        _empty_state("No export history found.")
    else:
        for h in filtered_h:
            st.markdown(
                f"<div class='nasmi-card'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<div>"
                f"<span style='font-weight:600;color:#e3f2fd;font-size:0.88rem;'>{h['name']}</span>"
                f"<div style='font-size:0.72rem;color:#546e7a;margin-top:0.2rem;'>"
                f"📅 {h['date']} · 📦 {h['size']} · 🗂️ {h['format']}</div>"
                f"</div>"
                f"{badge(h['type'], 'active')}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            col_dl, col_del = st.columns([4, 1])
            with col_dl:
                if st.button(
                    "⬇️ Download",
                    key=f"dl_{h['name']}_{h['date']}",
                    use_container_width=True,
                ):
                    st.toast(f"Downloading {h['name']}", icon="⬇️")
            with col_del:
                if st.button(
                    "🗑", key=f"del_{h['name']}_{h['date']}", use_container_width=True
                ):
                    st.toast(f"Deleted {h['name']}", icon="🗑")
            st.markdown(
                "<div style='margin-bottom:0.4rem;'></div>", unsafe_allow_html=True
            )
