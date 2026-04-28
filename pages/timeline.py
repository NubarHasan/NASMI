from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header(
    "📅",
    "Timeline",
    "Life events · document history · field changes — all in chronological order",
)


# ── Renderers ─────────────────────────────────────────
def _render_event(e: dict[str, object]) -> None:
    icon_map: dict[str, str] = {
        "document": "📄",
        "field": "✏️",
        "address": "🏠",
        "conflict": "⚠️",
        "identity": "🪪",
        "financial": "💰",
        "system": "⚙️",
    }
    icon = icon_map.get(str(e["category"]), "📌")
    st.markdown(
        f"<div class='nasmi-card' style='display:flex;gap:1rem;align-items:flex-start;'>"
        f"<div style='font-size:1.4rem;padding-top:0.1rem;'>{icon}</div>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<span style='font-weight:600;color:#e3f2fd;font-size:0.9rem;'>{e['title']}</span>"
        f"<div style='display:flex;gap:0.4rem;align-items:center;'>"
        f"{badge(str(e['category']), str(e['status']))}"
        f"<span style='font-size:0.72rem;color:#37474f;'>{e['date']}</span>"
        f"</div>"
        f"</div>"
        f"<div style='font-size:0.8rem;color:#546e7a;margin-top:0.2rem;'>{e['description']}</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.3rem;'>"
        f"📄 {e['source']}"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_year_divider(year: str) -> None:
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:0.8rem;margin:1rem 0 0.5rem 0;'>"
        f"<div style='flex:1;height:1px;background:#1e2d4a;'></div>"
        f"<span style='font-size:0.85rem;font-weight:700;color:#1565c0;"
        f"letter-spacing:2px;'>{year}</span>"
        f"<div style='flex:1;height:1px;background:#1e2d4a;'></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _empty_state(msg: str = "No events found.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:3rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Controls ──────────────────────────────────────────
col_cat, col_status, col_search, col_view = st.columns([2, 2, 3, 2])

with col_cat:
    cat_filter = st.selectbox(
        "Category",
        [
            "All",
            "document",
            "field",
            "address",
            "conflict",
            "identity",
            "financial",
            "system",
        ],
        label_visibility="collapsed",
        key="tl_cat",
    )

with col_status:
    status_filter = st.selectbox(
        "Status",
        ["All", "active", "expired", "pending", "conflict", "new"],
        label_visibility="collapsed",
        key="tl_status",
    )

with col_search:
    tl_search = st.text_input(
        "Search timeline",
        placeholder="Search events, documents, fields...",
        label_visibility="collapsed",
        key="tl_search",
    )

with col_view:
    tl_view = st.selectbox(
        "View",
        ["Chronological", "By Category", "By Document"],
        label_visibility="collapsed",
        key="tl_view",
    )

st.divider()

# ── Stats ─────────────────────────────────────────────
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Total Events", "—")
s2.metric("Documents", "—")
s3.metric("Field Changes", "—")
s4.metric("Conflicts", "—")
s5.metric("Last Event", "—")

st.divider()

# ── Mock Events ───────────────────────────────────────
mock_events: list[dict[str, object]] = [
    {
        "title": "Personalausweis uploaded",
        "description": "Identity document processed — 6 entities extracted",
        "category": "document",
        "status": "active",
        "source": "—",
        "date": "—",
        "year": "2024",
    },
    {
        "title": "Address updated",
        "description": "New address extracted from Meldebescheinigung",
        "category": "address",
        "status": "active",
        "source": "—",
        "date": "—",
        "year": "2024",
    },
    {
        "title": "IBAN conflict detected",
        "description": "Two different IBAN values found across documents",
        "category": "conflict",
        "status": "conflict",
        "source": "—",
        "date": "—",
        "year": "2024",
    },
    {
        "title": "Reisepass uploaded",
        "description": "Passport processed — nationality and expiry extracted",
        "category": "document",
        "status": "active",
        "source": "—",
        "date": "—",
        "year": "2023",
    },
    {
        "title": "Tax ID registered",
        "description": "Tax ID extracted from Steuerbescheid",
        "category": "identity",
        "status": "active",
        "source": "—",
        "date": "—",
        "year": "2023",
    },
]

# ── Filter Logic ──────────────────────────────────────
filtered: list[dict[str, object]] = list(mock_events)

if cat_filter != "All":
    filtered = [e for e in filtered if e["category"] == cat_filter]

if status_filter != "All":
    filtered = [e for e in filtered if e["status"] == status_filter]

if tl_search.strip():
    filtered = [
        e
        for e in filtered
        if tl_search.lower() in str(e["title"]).lower()
        or tl_search.lower() in str(e["description"]).lower()
        or tl_search.lower() in str(e["source"]).lower()
    ]

# ── Views ─────────────────────────────────────────────
if not filtered:
    _empty_state("No events match the current filter.")

elif tl_view == "Chronological":
    years: list[str] = sorted({str(e["year"]) for e in filtered}, reverse=True)
    for year in years:
        _render_year_divider(year)
        for e in filtered:
            if e["year"] == year:
                _render_event(e)

elif tl_view == "By Category":
    cats: list[str] = sorted({str(e["category"]) for e in filtered})
    for cat in cats:
        group = [e for e in filtered if e["category"] == cat]
        with st.expander(f"{cat.capitalize()}  ({len(group)} events)", expanded=True):
            for e in group:
                _render_event(e)

elif tl_view == "By Document":
    docs: list[str] = sorted({str(e["source"]) for e in filtered})
    for doc in docs:
        group = [e for e in filtered if e["source"] == doc]
        with st.expander(f"📄 {doc}  ({len(group)} events)", expanded=False):
            for e in group:
                _render_event(e)
