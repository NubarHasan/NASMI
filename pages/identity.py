from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header(
    "🪪", "Identity & Claims", "Identity Core 🔒 · Signed Claims · Export Certificates"
)


# ── Renderers ─────────────────────────────────────────
def _render_frozen_field(label: str, value: str, lock: str = "HARD") -> None:
    lock_color = "#ef9a9a" if lock == "HARD" else "#ffcc80"
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"padding:0.5rem 0;border-bottom:1px solid #1e2d4a;'>"
        f"<span style='font-size:0.78rem;color:#546e7a;width:35%;'>{label}</span>"
        f"<span style='font-size:0.88rem;color:#e3f2fd;font-weight:600;width:45%;'>{value}</span>"
        f"<span style='font-size:0.68rem;color:{lock_color};font-weight:700;"
        f"letter-spacing:0.5px;'>🔒 {lock}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_claim_card(claim: dict[str, object], idx: int) -> None:
    status = str(claim["status"])
    st.markdown(
        f"<div class='nasmi-card'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;'>"
        f"<span style='font-weight:700;color:#e3f2fd;font-size:0.92rem;'>{claim['title']}</span>"
        f"{badge(str(claim['type']), status)}"
        f"</div>"
        f"<div style='font-size:0.75rem;color:#546e7a;'>"
        f"📅 Issued: {claim['issued']} · ⏳ Expires: {claim['expires']}"
        f"</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.2rem;'>"
        f"🔑 Fields: {claim['fields']} · 📄 Source: {claim['source']}"
        f"</div>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    col_view, col_export, col_revoke = st.columns([2, 2, 2])
    with col_view:
        if st.button(
            "🔍 View Claim", key=f"claim_view_{idx}", use_container_width=True
        ):
            st.session_state[f"claim_open_{idx}"] = not st.session_state.get(
                f"claim_open_{idx}", False
            )
    with col_export:
        if st.button(
            "📤 Export Certificate", key=f"claim_export_{idx}", use_container_width=True
        ):
            st.toast(f"Exporting: {claim['title']}", icon="📤")
    with col_revoke:
        if st.button("🚫 Revoke", key=f"claim_revoke_{idx}", use_container_width=True):
            st.toast(f"Revoked: {claim['title']}", icon="🚫")

    if st.session_state.get(f"claim_open_{idx}"):
        st.markdown(
            "<div class='nasmi-card' style='background:#0d1b2a;margin-top:0.3rem;'>"
            "<div style='font-size:0.75rem;color:#546e7a;margin-bottom:0.5rem;'>CLAIM FIELDS</div>",
            unsafe_allow_html=True,
        )
        mock_fields: list[dict[str, str]] = [
            {"field": "Full Name", "value": "—", "verified": "Yes"},
            {"field": "Date of Birth", "value": "—", "verified": "Yes"},
            {"field": "Nationality", "value": "—", "verified": "Yes"},
        ]
        for f in mock_fields:
            st.markdown(
                f"<div style='display:flex;gap:1rem;align-items:center;"
                f"padding:0.3rem 0;border-bottom:1px solid #1e2d4a;'>"
                f"<span style='font-size:0.75rem;color:#546e7a;width:30%;'>{f['field']}</span>"
                f"<span style='font-size:0.82rem;color:#e3f2fd;width:45%;'>{f['value']}</span>"
                f"<span style='font-size:0.7rem;color:#a5d6a7;width:25%;'>✔ {f['verified']}</span>"
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
tab_core, tab_claims, tab_export = st.tabs(
    [
        "🔒 Identity Core",
        "📜 Signed Claims",
        "📤 Export Certificate",
    ]
)


# ══════════════════════════════════════════════════════
# TAB 1 — Identity Core
# ══════════════════════════════════════════════════════
with tab_core:
    st.markdown(
        "<div class='nasmi-card' style='border-left:3px solid #ef9a9a;margin-bottom:1rem;'>"
        "<div style='font-size:0.78rem;color:#ef9a9a;font-weight:600;'>"
        "🔒 FROZEN — Identity Core is read-only. "
        "Manual updates only via Settings → Identity Core."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_id, col_score = st.columns([3, 1])

    with col_id:
        st.markdown(
            "<div class='nasmi-card'>"
            "<div style='font-size:0.85rem;font-weight:700;color:#e3f2fd;"
            "margin-bottom:0.8rem;'>👤 Core Identity Fields</div>",
            unsafe_allow_html=True,
        )
        _render_frozen_field("Full Name", "—", "HARD")
        _render_frozen_field("Date of Birth", "—", "HARD")
        _render_frozen_field("Nationality", "—", "HARD")
        _render_frozen_field("ID Number", "—", "HARD")
        _render_frozen_field("ID Type", "—", "HARD")
        _render_frozen_field("Verified", "—", "HARD")
        _render_frozen_field("Lock Level", "HARD", "HARD")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_score:
        st.markdown(
            "<div class='nasmi-card' style='text-align:center;'>"
            "<div style='font-size:0.75rem;color:#546e7a;margin-bottom:0.5rem;'>"
            "TRUST SCORE</div>"
            "<div style='font-size:2.5rem;font-weight:700;color:#a5d6a7;'>—</div>"
            "<div style='font-size:0.7rem;color:#37474f;margin-top:0.3rem;'>"
            "Identity Verified</div>"
            "</div>"
            "<div class='nasmi-card' style='text-align:center;margin-top:0.5rem;'>"
            "<div style='font-size:0.75rem;color:#546e7a;margin-bottom:0.5rem;'>"
            "DOCUMENTS</div>"
            "<div style='font-size:2rem;font-weight:700;color:#e3f2fd;'>—</div>"
            "<div style='font-size:0.7rem;color:#37474f;margin-top:0.3rem;'>"
            "Linked to identity</div>"
            "</div>"
            "<div class='nasmi-card' style='text-align:center;margin-top:0.5rem;'>"
            "<div style='font-size:0.75rem;color:#546e7a;margin-bottom:0.5rem;'>"
            "LAST VERIFIED</div>"
            "<div style='font-size:0.85rem;font-weight:600;color:#e3f2fd;'>—</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    st.markdown(
        "<div class='nasmi-card'>"
        "<div style='font-size:0.85rem;font-weight:700;color:#e3f2fd;"
        "margin-bottom:0.8rem;'>📊 Identity Completeness</div>",
        unsafe_allow_html=True,
    )
    completeness_fields: list[dict[str, object]] = [
        {"field": "Full Name", "filled": True},
        {"field": "Date of Birth", "filled": True},
        {"field": "Nationality", "filled": True},
        {"field": "ID Number", "filled": True},
        {"field": "ID Type", "filled": True},
        {"field": "Verified", "filled": False},
    ]
    for cf in completeness_fields:
        icon = "✅" if cf["filled"] else "⬜"
        color = "#a5d6a7" if cf["filled"] else "#37474f"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:0.5rem;"
            f"padding:0.25rem 0;'>"
            f"<span>{icon}</span>"
            f"<span style='font-size:0.8rem;color:{color};'>{cf['field']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# TAB 2 — Signed Claims
# ══════════════════════════════════════════════════════
with tab_claims:
    col_new, col_filter = st.columns([3, 2])
    with col_new:
        if st.button("➕ Generate New Claim", use_container_width=True):
            st.session_state["new_claim_open"] = not st.session_state.get(
                "new_claim_open", False
            )
    with col_filter:
        claim_filter = st.selectbox(
            "Filter",
            ["All", "active", "expired", "revoked"],
            label_visibility="collapsed",
            key="id_claim_filter",
        )

    if st.session_state.get("new_claim_open"):
        st.markdown(
            "<div class='nasmi-card' style='margin-top:0.5rem;'>",
            unsafe_allow_html=True,
        )
        claim_title = st.text_input(
            "Claim Title", placeholder="e.g. Identity Proof", key="new_claim_title"
        )
        claim_type = st.selectbox(
            "Claim Type",
            ["Identity", "Address", "Financial", "Employment", "Custom"],
            key="new_claim_type",
        )
        claim_fields = st.multiselect(
            "Include Fields",
            [
                "Full Name",
                "Date of Birth",
                "Nationality",
                "ID Number",
                "Address",
                "IBAN",
                "Tax ID",
            ],
            key="new_claim_fields",
        )
        claim_expiry = st.date_input("Expiry Date", key="new_claim_expiry")
        col_gen, col_discard = st.columns([3, 1])
        with col_gen:
            if st.button(
                "🔑 Generate Claim", use_container_width=True, key="gen_claim_btn"
            ):
                if claim_title.strip() and claim_fields:
                    st.toast(f"Claim generated: {claim_title}", icon="🔑")
                    st.session_state["new_claim_open"] = False
                else:
                    st.warning("Title and at least one field are required.")
        with col_discard:
            if st.button(
                "✖ Discard", use_container_width=True, key="discard_claim_btn"
            ):
                st.session_state["new_claim_open"] = False
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Claims", "—")
    c2.metric("Active", "—")
    c3.metric("Expired", "—")

    st.divider()

    mock_claims: list[dict[str, object]] = [
        {
            "title": "Identity Proof",
            "type": "Identity",
            "issued": "—",
            "expires": "—",
            "fields": 3,
            "source": "Personalausweis",
            "status": "active",
        },
        {
            "title": "Address Proof",
            "type": "Address",
            "issued": "—",
            "expires": "—",
            "fields": 2,
            "source": "Meldebescheinigung",
            "status": "active",
        },
        {
            "title": "Financial Proof",
            "type": "Financial",
            "issued": "—",
            "expires": "—",
            "fields": 2,
            "source": "Kontoauszug",
            "status": "expired",
        },
    ]

    filtered_c: list[dict[str, object]] = list(mock_claims)
    if claim_filter != "All":
        filtered_c = [c for c in filtered_c if c["status"] == claim_filter]

    if not filtered_c:
        _empty_state("No claims found.")
    for idx, claim in enumerate(filtered_c):
        _render_claim_card(claim, idx)


# ══════════════════════════════════════════════════════
# TAB 3 — Export Certificate
# ══════════════════════════════════════════════════════
with tab_export:
    st.markdown(
        "<div class='nasmi-card'>"
        "<div style='font-size:0.9rem;font-weight:700;color:#e3f2fd;"
        "margin-bottom:1rem;'>📤 Export Identity Certificate</div>"
        "<div style='font-size:0.8rem;color:#546e7a;'>"
        "Generate a signed identity certificate containing selected fields "
        "from the Identity Core and active claims."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    col_fmt, col_scope = st.columns(2)
    with col_fmt:
        cert_format = st.selectbox(
            "Export Format",
            ["PDF Certificate", "JSON", "Both"],
            key="cert_format",
        )
    with col_scope:
        cert_scope = st.selectbox(
            "Include",
            ["Identity Core Only", "Identity + Active Claims", "Full Identity Report"],
            key="cert_scope",
        )

    cert_fields = st.multiselect(
        "Select Fields to Include",
        ["Full Name", "Date of Birth", "Nationality", "ID Number", "ID Type"],
        default=["Full Name", "Date of Birth", "Nationality"],
        key="cert_fields",
    )

    st.checkbox("Include QR Code", value=True, key="cert_qr")
    st.checkbox("Include Audit Trail", value=False, key="cert_audit")

    st.divider()

    if st.button("📤 Generate Certificate", use_container_width=True):
        if cert_fields:
            with st.spinner("Generating certificate..."):
                st.toast("Certificate generated successfully", icon="📤")
        else:
            st.warning("Select at least one field.")
