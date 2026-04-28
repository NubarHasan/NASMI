from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge
from db.database import Database

apply_theme()
page_header(
    "📒",
    "Address & Field Book",
    "All known addresses · contacts · field values — tracked and versioned",
)


# ── DB Loaders ────────────────────────────────────────
def _load_addresses() -> list[dict]:
    try:
        with Database() as db:
            rows = db.fetchall(
                """
                SELECT ab.id, ab.label, ab.street, ab.city, ab.country,
                       ab.status, ab.since, ab.source, ab.confidence, ab.conflict,
                       COUNT(v.id) AS versions
                FROM address_book ab
                LEFT JOIN versioning v ON v.record_id = ab.id AND v.table_name = 'address_book'
                GROUP BY ab.id
                ORDER BY ab.since DESC
                """
            )
            return [
                {
                    "id": r["id"],
                    "label": r["label"] or "Address",
                    "street": r["street"] or "—",
                    "city": r["city"] or "—",
                    "country": r["country"] or "—",
                    "source": r["source"] or "—",
                    "since": str(r["since"] or "—")[:10],
                    "confidence": int(r["confidence"] or 0),
                    "status": r["status"] or "active",
                    "versions": int(r["versions"] or 1),
                    "conflict": bool(r["conflict"]),
                }
                for r in rows
            ]
    except Exception:
        return []


def _load_fields() -> list[dict]:
    try:
        with Database() as db:
            rows = db.fetchall(
                """
                SELECT fb.id, fb.field, fb.value, fb.type, fb.source,
                       fb.date, fb.confidence, fb.status, fb.conflict,
                       COUNT(v.id) AS versions
                FROM field_book fb
                LEFT JOIN versioning v ON v.record_id = fb.id AND v.table_name = 'field_book'
                GROUP BY fb.id
                ORDER BY fb.date DESC
                """
            )
            return [
                {
                    "id": r["id"],
                    "field": r["field"] or "—",
                    "value": r["value"] or "—",
                    "type": r["type"] or "OTHER",
                    "source": r["source"] or "—",
                    "date": str(r["date"] or "—")[:10],
                    "confidence": int(r["confidence"] or 0),
                    "status": r["status"] or "new",
                    "versions": int(r["versions"] or 1),
                    "conflict": bool(r["conflict"]),
                }
                for r in rows
            ]
    except Exception:
        return []


def _load_contacts() -> list[dict]:
    try:
        with Database() as db:
            rows = db.fetchall(
                """
                SELECT id, name, role, organization, phone, email, source, created_at
                FROM contacts
                ORDER BY created_at DESC
                """
            )
            return [
                {
                    "id": r["id"],
                    "name": r["name"] or "—",
                    "role": r["role"] or "—",
                    "organization": r["organization"] or "—",
                    "phone": r["phone"] or "—",
                    "email": r["email"] or "—",
                    "source": r["source"] or "—",
                    "created_at": str(r["created_at"] or "—")[:10],
                }
                for r in rows
            ]
    except Exception:
        return []


# ── Renderers ─────────────────────────────────────────
def _render_address(a: dict) -> None:
    confidence = a["confidence"]
    conf_color = (
        "#a5d6a7" if confidence >= 80 else "#ffcc80" if confidence >= 50 else "#ef9a9a"
    )
    conflict_badge = f"&nbsp;{badge('⚠ CONFLICT', 'conflict')}" if a["conflict"] else ""
    st.markdown(
        f"<div class='nasmi-card'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;'>"
        f"{badge(a['label'], a['status'])}{conflict_badge}"
        f"</div>"
        f"<div style='font-size:1rem;font-weight:600;color:#e3f2fd;'>{a['street']}</div>"
        f"<div style='font-size:0.85rem;color:#90a4ae;'>{a['city']} · {a['country']}</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.3rem;'>"
        f"📄 {a['source']} · 📅 {a['since']} · 🔁 {a['versions']} version{'s' if a['versions'] != 1 else ''}"
        f"</div>"
        f"</div>"
        f"<span style='font-size:0.72rem;color:{conf_color};font-weight:600;'>"
        f"Confidence: {confidence}%</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_field(f: dict) -> None:
    confidence = f["confidence"]
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
        f"{badge(f['type'], f['status'])}{conflict_badge}"
        f"</div>"
        f"<div style='font-size:1rem;font-weight:600;color:#e3f2fd;margin-top:0.2rem;'>{f['value']}</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.2rem;'>"
        f"📄 {f['source']} · 📅 {f['date']} · 🔁 {f['versions']} version{'s' if f['versions'] != 1 else ''}"
        f"</div>"
        f"</div>"
        f"<span style='font-size:0.72rem;color:{conf_color};font-weight:600;'>"
        f"Confidence: {confidence}%</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_contact(c: dict) -> None:
    st.markdown(
        f"<div class='nasmi-card'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='font-weight:700;color:#e3f2fd;font-size:0.95rem;'>{c['name']}</div>"
        f"<div style='font-size:0.8rem;color:#90a4ae;'>{c['role']} · {c['organization']}</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.3rem;'>"
        f"📞 {c['phone']} · ✉️ {c['email']}"
        f"</div>"
        f"</div>"
        f"<span style='font-size:0.7rem;color:#37474f;'>📄 {c['source']} · 📅 {c['created_at']}</span>"
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

all_addresses = _load_addresses()
all_fields = _load_fields()
all_contacts = _load_contacts()


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
        addr_sort = st.selectbox(
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
    a1.metric("Total Addresses", len(all_addresses))
    a2.metric("Current", sum(1 for a in all_addresses if a["label"] == "Current"))
    a3.metric("Conflicts", sum(1 for a in all_addresses if a["conflict"]))

    st.divider()

    filtered_addr = list(all_addresses)
    if addr_filter == "Conflict":
        filtered_addr = [a for a in filtered_addr if a["conflict"]]
    elif addr_filter != "All":
        filtered_addr = [a for a in filtered_addr if a["label"] == addr_filter]

    if addr_sort == "Confidence ↓":
        filtered_addr.sort(key=lambda x: x["confidence"], reverse=True)
    elif addr_sort == "Alphabetical":
        filtered_addr.sort(key=lambda x: x["city"])

    if addr_search.strip():
        q = addr_search.lower()
        filtered_addr = [
            a
            for a in filtered_addr
            if q in a["street"].lower()
            or q in a["city"].lower()
            or q in a["country"].lower()
        ]

    if not filtered_addr:
        _empty_state("No addresses found.")
    else:
        for a in filtered_addr:
            _render_address(a)


# ══════════════════════════════════════════════════════
# TAB 2 — Field Registry
# ══════════════════════════════════════════════════════
with tab_fields:
    col_ftype, col_fsearch = st.columns([2, 4])

    with col_ftype:
        types = ["All"] + sorted({f["type"] for f in all_fields})
        field_type = st.selectbox(
            "Field Type",
            types,
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
    f1.metric("Total Fields", len(all_fields))
    f2.metric("Filled", sum(1 for f in all_fields if f["value"] != "—"))
    f3.metric("Empty", sum(1 for f in all_fields if f["value"] == "—"))
    f4.metric("Conflicts", sum(1 for f in all_fields if f["conflict"]))

    st.divider()

    filtered_fields = list(all_fields)
    if field_type != "All":
        filtered_fields = [f for f in filtered_fields if f["type"] == field_type]
    if field_search.strip():
        q = field_search.lower()
        filtered_fields = [
            f
            for f in filtered_fields
            if q in f["field"].lower() or q in f["value"].lower()
        ]

    if not filtered_fields:
        _empty_state("No fields found.")
    else:
        for f in filtered_fields:
            _render_field(f)


# ══════════════════════════════════════════════════════
# TAB 3 — Contacts
# ══════════════════════════════════════════════════════
with tab_contacts:
    col_cs, col_cb = st.columns([4, 1])
    with col_cs:
        contact_search = st.text_input(
            "Search contacts",
            placeholder="Search by name, role, organization...",
            label_visibility="collapsed",
            key="contact_search",
        )
    with col_cb:
        st.button("➕ Add Contact", use_container_width=True, key="add_contact")

    st.divider()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Contacts", len(all_contacts))
    c2.metric("Organizations", sum(1 for c in all_contacts if c["organization"] != "—"))
    c3.metric("Individuals", sum(1 for c in all_contacts if c["organization"] == "—"))

    st.divider()

    filtered_contacts = list(all_contacts)
    if contact_search.strip():
        q = contact_search.lower()
        filtered_contacts = [
            c
            for c in filtered_contacts
            if q in c["name"].lower()
            or q in c["role"].lower()
            or q in c["organization"].lower()
        ]

    if not filtered_contacts:
        _empty_state(
            "No contacts yet — they will be extracted automatically from documents."
        )
    else:
        for c in filtered_contacts:
            _render_contact(c)
