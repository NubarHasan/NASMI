from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header(
    "📒",
    "Address & Field Book",
    "All known addresses · contacts · field values — tracked and versioned",
)


# ── Renderers ─────────────────────────────────────────
def _render_address(a: dict[str, object]) -> None:
    status = str(a["status"])
    confidence = int(a["confidence"])  # type: ignore[arg-type]
    conf_color = (
        "#a5d6a7" if confidence >= 80 else "#ffcc80" if confidence >= 50 else "#ef9a9a"
    )
    conflict_badge = f"&nbsp;{badge('⚠ CONFLICT', 'conflict')}" if a["conflict"] else ""
    st.markdown(
        f"<div class='nasmi-card'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;'>"
        f"{badge(str(a['label']), status)}"
        f"{conflict_badge}"
        f"</div>"
        f"<div style='font-size:1rem;font-weight:600;color:#e3f2fd;'>{a['street']}</div>"
        f"<div style='font-size:0.85rem;color:#90a4ae;'>{a['city']} · {a['country']}</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.3rem;'>"
        f"📄 {a['source']} · 📅 {a['since']} · 🔁 {a['versions']} version{'s' if a['versions'] != 1 else ''}"
        f"</div>"
        f"</div>"
        f"<div style='display:flex;flex-direction:column;align-items:flex-end;gap:0.4rem;'>"
        f"<span style='font-size:0.72rem;color:{conf_color};font-weight:600;'>"
        f"Confidence: {confidence}%</span>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_field(f: dict[str, object]) -> None:
    confidence = int(f["confidence"])  # type: ignore[arg-type]
    conf_color = (
        "#a5d6a7" if confidence >= 80 else "#ffcc80" if confidence >= 50 else "#ef9a9a"
    )
    conflict_badge = f"&nbsp;{badge('⚠ CONFLICT', 'conflict')}" if f["conflict"] else ""
    st.markdown(
        f"<div class='nasmi-card'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;'>"
        f"<span style='font-size:0.75rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;'>{f['field']}</span>"
        f"{badge(str(f['type']), str(f['status']))}"
        f"{conflict_badge}"
        f"</div>"
        f"<div style='font-size:1rem;font-weight:600;color:#e3f2fd;margin-top:0.2rem;'>"
        f"{f['value']}</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.2rem;'>"
        f"📄 {f['source']} · 📅 {f['date']} · "
        f"🔁 {f['versions']} version{'s' if f['versions'] != 1 else ''}"
        f"</div>"
        f"</div>"
        f"<span style='font-size:0.72rem;color:{conf_color};font-weight:600;'>"
        f"Confidence: {confidence}%</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _empty_state(msg: str = "No entries found.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:3rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Tabs ──────────────────────────────────────────────
tab_addr, tab_fields, tab_contacts = st.tabs(
    [
        "🏠 Address Book",
        "🗂️ Field Registry",
        "👤 Contacts",
    ]
)


# ══════════════════════════════════════════════════════
# TAB 1 — Address Book
# ══════════════════════════════════════════════════════
with tab_addr:
    col_filter, col_sort, col_search = st.columns([2, 2, 3])

    with col_filter:
        addr_filter = st.selectbox(
            "Status",
            ["All", "Current", "Previous", "Conflict"],
            label_visibility="collapsed",
            key="addr_filter",
        )
    with col_sort:
        st.selectbox(
            "Sort",
            ["Date ↓", "Confidence ↓", "Alphabetical"],
            label_visibility="collapsed",
            key="addr_sort",
        )
    with col_search:
        addr_search = st.text_input(
            "Search addresses",
            placeholder="Search by city, street, country...",
            label_visibility="collapsed",
            key="addr_search",
        )

    st.divider()

    a1, a2, a3 = st.columns(3)
    a1.metric("Total Addresses", "—")
    a2.metric("Current", "—")
    a3.metric("Conflicts", "—")

    st.divider()

    mock_addresses: list[dict[str, object]] = [
        {
            "label": "Current",
            "street": "—",
            "city": "—",
            "country": "—",
            "source": "—",
            "since": "—",
            "confidence": 0,
            "status": "active",
            "versions": 1,
            "conflict": False,
        },
        {
            "label": "Previous",
            "street": "—",
            "city": "—",
            "country": "—",
            "source": "—",
            "since": "—",
            "confidence": 0,
            "status": "expired",
            "versions": 1,
            "conflict": False,
        },
    ]

    filtered_addr: list[dict[str, object]] = list(mock_addresses)
    if addr_filter != "All":
        filtered_addr = [a for a in filtered_addr if a["label"] == addr_filter]
    if addr_search.strip():
        filtered_addr = [
            a
            for a in filtered_addr
            if addr_search.lower() in str(a["street"]).lower()
            or addr_search.lower() in str(a["city"]).lower()
            or addr_search.lower() in str(a["country"]).lower()
        ]

    if not filtered_addr:
        _empty_state("No addresses found.")
    for a in filtered_addr:
        _render_address(a)


# ══════════════════════════════════════════════════════
# TAB 2 — Field Registry
# ══════════════════════════════════════════════════════
with tab_fields:
    col_ftype, col_fsearch = st.columns([2, 4])

    with col_ftype:
        field_type = st.selectbox(
            "Field Type",
            ["All", "PERSON", "DATE", "ID", "FINANCE", "GPE", "ADDRESS", "OTHER"],
            label_visibility="collapsed",
            key="field_type",
        )
    with col_fsearch:
        field_search = st.text_input(
            "Search fields",
            placeholder="Search by field name or value...",
            label_visibility="collapsed",
            key="field_search",
        )

    st.divider()

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Total Fields", "—")
    f2.metric("Filled", "—")
    f3.metric("Empty", "—")
    f4.metric("Conflicts", "—")

    st.divider()

    mock_fields: list[dict[str, object]] = [
        {
            "field": "Full Name",
            "value": "—",
            "type": "PERSON",
            "source": "—",
            "date": "—",
            "confidence": 0,
            "status": "new",
            "versions": 1,
            "conflict": False,
        },
        {
            "field": "Date of Birth",
            "value": "—",
            "type": "DATE",
            "source": "—",
            "date": "—",
            "confidence": 0,
            "status": "new",
            "versions": 1,
            "conflict": False,
        },
        {
            "field": "Tax ID",
            "value": "—",
            "type": "ID",
            "source": "—",
            "date": "—",
            "confidence": 0,
            "status": "new",
            "versions": 1,
            "conflict": False,
        },
        {
            "field": "IBAN",
            "value": "—",
            "type": "FINANCE",
            "source": "—",
            "date": "—",
            "confidence": 0,
            "status": "new",
            "versions": 1,
            "conflict": False,
        },
        {
            "field": "Nationality",
            "value": "—",
            "type": "GPE",
            "source": "—",
            "date": "—",
            "confidence": 0,
            "status": "new",
            "versions": 1,
            "conflict": False,
        },
        {
            "field": "Social Security",
            "value": "—",
            "type": "ID",
            "source": "—",
            "date": "—",
            "confidence": 0,
            "status": "new",
            "versions": 1,
            "conflict": False,
        },
    ]

    filtered_fields: list[dict[str, object]] = list(mock_fields)
    if field_type != "All":
        filtered_fields = [f for f in filtered_fields if f["type"] == field_type]
    if field_search.strip():
        filtered_fields = [
            f
            for f in filtered_fields
            if field_search.lower() in str(f["field"]).lower()
            or field_search.lower() in str(f["value"]).lower()
        ]

    if not filtered_fields:
        _empty_state("No fields found.")
    for f in filtered_fields:
        _render_field(f)


# ══════════════════════════════════════════════════════
# TAB 3 — Contacts
# ══════════════════════════════════════════════════════
with tab_contacts:
    col_cs, col_cb = st.columns([4, 1])
    with col_cs:
        st.text_input(
            "Search contacts",
            placeholder="Search by name, role, organization...",
            label_visibility="collapsed",
            key="contact_search",
        )
    with col_cb:
        st.button("➕ Add Contact", use_container_width=True)

    st.divider()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Contacts", "—")
    c2.metric("Organizations", "—")
    c3.metric("Individuals", "—")

    st.divider()

    _empty_state(
        "No contacts yet — they will be extracted automatically from documents."
    )
