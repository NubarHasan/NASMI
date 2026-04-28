from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge
from db.database import Database

apply_theme()
page_header(
    "📅",
    "Timeline",
    "Life events · document history · field changes — all in chronological order",
)


# ── DB Loader ─────────────────────────────────────────
def _load_events() -> list[dict]:
    try:
        with Database() as db:
            rows = db.fetchall(
                """
                SELECT title, description, category, status, source, event_date
                FROM events
                ORDER BY event_date DESC
                """
            )
            return [
                {
                    "title": r["title"] or "—",
                    "description": r["description"] or "—",
                    "category": r["category"] or "system",
                    "status": r["status"] or "active",
                    "source": r["source"] or "—",
                    "date": str(r["event_date"] or "—")[:10],
                    "year": str(r["event_date"] or "—")[:4],
                }
                for r in rows
            ]
    except Exception:
        return []


def _load_stats(events: list[dict]) -> dict:
    return {
        "total": len(events),
        "docs": sum(1 for e in events if e["category"] == "document"),
        "fields": sum(1 for e in events if e["category"] == "field"),
        "conflicts": sum(1 for e in events if e["category"] == "conflict"),
        "last": events[0]["date"] if events else "—",
    }


# ── Renderers ─────────────────────────────────────────
def _render_event(e: dict) -> None:
    icon_map = {
        "document": "📄",
        "field": "✏️",
        "address": "🏠",
        "conflict": "⚠️",
        "identity": "🪪",
        "financial": "💰",
        "system": "⚙️",
    }
    icon = icon_map.get(e["category"], "📌")
    st.markdown(
        f"<div class='nasmi-card' style='display:flex;gap:1rem;align-items:flex-start;'>"
        f"<div style='font-size:1.4rem;padding-top:0.1rem;'>{icon}</div>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<span style='font-weight:600;color:#e3f2fd;font-size:0.9rem;'>{e['title']}</span>"
        f"<div style='display:flex;gap:0.4rem;align-items:center;'>"
        f"{badge(e['category'], e['status'])}"
        f"<span style='font-size:0.72rem;color:#37474f;'>{e['date']}</span>"
        f"</div>"
        f"</div>"
        f"<div style='font-size:0.8rem;color:#546e7a;margin-top:0.2rem;'>{e['description']}</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.3rem;'>📄 {e['source']}</div>"
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
all_events = _load_events()
stats = _load_stats(all_events)

col_cat, col_status, col_search, col_view = st.columns([2, 2, 3, 2])

with col_cat:
    categories = ["All"] + sorted({e["category"] for e in all_events})
    cat_filter = st.selectbox(
        "Category",
        categories,
        label_visibility="collapsed",
        key="tl_cat",
    )

with col_status:
    statuses = ["All"] + sorted({e["status"] for e in all_events})
    status_filter = st.selectbox(
        "Status",
        statuses,
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
s1.metric("Total Events", stats["total"])
s2.metric("Documents", stats["docs"])
s3.metric("Field Changes", stats["fields"])
s4.metric("Conflicts", stats["conflicts"])
s5.metric("Last Event", stats["last"])

st.divider()

# ── Filter Logic ──────────────────────────────────────
filtered = list(all_events)

if cat_filter != "All":
    filtered = [e for e in filtered if e["category"] == cat_filter]

if status_filter != "All":
    filtered = [e for e in filtered if e["status"] == status_filter]

if tl_search.strip():
    q = tl_search.lower()
    filtered = [
        e
        for e in filtered
        if q in e["title"].lower()
        or q in e["description"].lower()
        or q in e["source"].lower()
    ]

# ── Views ─────────────────────────────────────────────
if not filtered:
    _empty_state("No events match the current filter.")

elif tl_view == "Chronological":
    years = sorted({e["year"] for e in filtered}, reverse=True)
    for year in years:
        _render_year_divider(year)
        for e in [x for x in filtered if x["year"] == year]:
            _render_event(e)

elif tl_view == "By Category":
    cats = sorted({e["category"] for e in filtered})
    for cat in cats:
        group = [e for e in filtered if e["category"] == cat]
        with st.expander(f"{cat.capitalize()}  ({len(group)} events)", expanded=True):
            for e in group:
                _render_event(e)

elif tl_view == "By Document":
    docs = sorted({e["source"] for e in filtered})
    for doc in docs:
        group = [e for e in filtered if e["source"] == doc]
        with st.expander(f"📄 {doc}  ({len(group)} events)", expanded=False):
            for e in group:
                _render_event(e)
