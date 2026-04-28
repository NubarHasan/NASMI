from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header(
    "🧠",
    "Knowledge Base",
    "All extracted knowledge — entities · values · sources · trust scores",
)


def _render_entry(e: dict[str, object]) -> None:
    trust = int(e["trust"])  # type: ignore[arg-type]
    confidence = int(e["confidence"])  # type: ignore[arg-type]
    trust_color = "#a5d6a7" if trust >= 80 else "#ffcc80" if trust >= 50 else "#ef9a9a"
    conflict_badge = f"&nbsp;{badge('⚠ CONFLICT', 'conflict')}" if e["conflict"] else ""
    st.markdown(
        f"<div class='nasmi-card'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;'>"
        f"<span style='font-size:0.75rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;'>{e['entity']}</span>"
        f"{badge(str(e['type']), str(e['status']))}"
        f"{conflict_badge}"
        f"</div>"
        f"<div style='font-size:1.05rem;font-weight:600;color:#e3f2fd;margin-top:0.3rem;'>"
        f"{e['value']}</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.3rem;'>"
        f"📄 {e['source']} · {e['doc_type']} · 📅 {e['date']} · "
        f"🔁 {e['versions']} version{'s' if e['versions'] != 1 else ''}"
        f"</div>"
        f"</div>"
        f"<div style='display:flex;flex-direction:column;align-items:flex-end;gap:0.4rem;'>"
        f"<span style='font-size:0.72rem;color:{trust_color};font-weight:600;'>"
        f"Trust: {trust}%</span>"
        f"<span style='font-size:0.72rem;color:#546e7a;'>"
        f"Confidence: {confidence}%</span>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _empty_state() -> None:
    st.markdown(
        "<div class='nasmi-card' style='text-align:center;padding:3rem;"
        "color:#37474f;'>No entries match the current filter.</div>",
        unsafe_allow_html=True,
    )


if "kb_view" not in st.session_state:
    st.session_state.kb_view = "By Entity Type"
if "kb_filter" not in st.session_state:
    st.session_state.kb_filter = "All"

col_view, col_filter, col_sort, col_search = st.columns([2, 2, 2, 3])

with col_view:
    view = st.selectbox(
        "View",
        ["By Entity Type", "By Document", "By Date", "Flat List"],
        label_visibility="collapsed",
    )
with col_filter:
    kb_filter = st.selectbox(
        "Filter",
        ["All", "PERSON", "DATE", "ADDRESS", "ID", "FINANCE", "GPE", "OTHER"],
        label_visibility="collapsed",
    )
with col_sort:
    st.selectbox(
        "Sort",
        ["Trust Score ↓", "Date Added ↓", "Confidence ↓", "Alphabetical"],
        label_visibility="collapsed",
    )
with col_search:
    kb_search = st.text_input(
        "Search KB",
        placeholder="Filter knowledge entries...",
        label_visibility="collapsed",
    )

st.divider()

s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Total Entries", "—")
s2.metric("Unique Entities", "—")
s3.metric("Avg Trust Score", "—")
s4.metric("Conflicts", "—")
s5.metric("Last Updated", "—")

st.divider()

mock_kb: list[dict[str, object]] = [
    {
        "entity": "Full Name",
        "value": "—",
        "type": "PERSON",
        "source": "—",
        "doc_type": "Personalausweis",
        "trust": 0,
        "confidence": 0,
        "status": "new",
        "date": "—",
        "versions": 1,
        "conflict": False,
    },
    {
        "entity": "Date of Birth",
        "value": "—",
        "type": "DATE",
        "source": "—",
        "doc_type": "Personalausweis",
        "trust": 0,
        "confidence": 0,
        "status": "new",
        "date": "—",
        "versions": 1,
        "conflict": False,
    },
    {
        "entity": "Address",
        "value": "—",
        "type": "ADDRESS",
        "source": "—",
        "doc_type": "Meldebescheinigung",
        "trust": 0,
        "confidence": 0,
        "status": "pending",
        "date": "—",
        "versions": 2,
        "conflict": True,
    },
    {
        "entity": "IBAN",
        "value": "—",
        "type": "FINANCE",
        "source": "—",
        "doc_type": "Kontoauszug",
        "trust": 0,
        "confidence": 0,
        "status": "new",
        "date": "—",
        "versions": 1,
        "conflict": False,
    },
    {
        "entity": "Nationality",
        "value": "—",
        "type": "GPE",
        "source": "—",
        "doc_type": "Reisepass",
        "trust": 0,
        "confidence": 0,
        "status": "active",
        "date": "—",
        "versions": 1,
        "conflict": False,
    },
]

filtered: list[dict[str, object]] = list(mock_kb)

if kb_filter != "All":
    filtered = [e for e in filtered if e["type"] == kb_filter]

if kb_search.strip():
    filtered = [
        e
        for e in filtered
        if kb_search.lower() in str(e["entity"]).lower()
        or kb_search.lower() in str(e["value"]).lower()
    ]

if view == "By Entity Type":
    entity_types: list[str] = sorted({str(e["type"]) for e in filtered})
    if not entity_types:
        _empty_state()
    for etype in entity_types:
        group = [e for e in filtered if e["type"] == etype]
        with st.expander(f"{etype}  ({len(group)} entries)", expanded=True):
            for e in group:
                _render_entry(e)

elif view == "Flat List":
    if not filtered:
        _empty_state()
    for e in filtered:
        _render_entry(e)

elif view == "By Document":
    docs: list[str] = sorted({str(e["source"]) for e in filtered})
    if not docs:
        _empty_state()
    for doc in docs:
        group = [e for e in filtered if e["source"] == doc]
        with st.expander(f"📄 {doc}  ({len(group)} entries)", expanded=False):
            for e in group:
                _render_entry(e)

elif view == "By Date":
    dates: list[str] = sorted({str(e["date"]) for e in filtered}, reverse=True)
    if not dates:
        _empty_state()
    for d in dates:
        group = [e for e in filtered if e["date"] == d]
        with st.expander(f"📅 {d}  ({len(group)} entries)", expanded=False):
            for e in group:
                _render_entry(e)
