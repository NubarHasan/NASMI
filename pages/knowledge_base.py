from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge
from db.database import Database
from knowledge.quality_engine import QualityEngine

apply_theme()
page_header(
    "🧠",
    "Knowledge Base",
    "Confirmed knowledge — verified entities · trust scores · sources",
)

_qe = QualityEngine()


# ── Loaders ────────────────────────────────────────────────────────────────


def _load_kb() -> list[dict]:
    try:
        with Database() as db:
            rows = db.fetchall(
                """
                SELECT
                    k.field,
                    k.value,
                    k.confidence,
                    k.source,
                    k.verified,
                    k.updated_at,
                    (
                        SELECT COUNT(*) FROM entities e
                        WHERE e.entity_type = k.field
                          AND e.source      = k.source
                    ) AS versions
                FROM knowledge k
                ORDER BY k.updated_at DESC
                """,
            )

            conflict_fields: set[str] = set()
            for c in db.fetchall("SELECT field FROM contradictions"):
                conflict_fields.add(c["field"])

        result = []
        for r in rows:
            trust = int((r["confidence"] or 0) * 100)
            result.append(
                {
                    "field": r["field"] or "—",
                    "value": r["value"] or "—",
                    "source": r["source"] or "—",
                    "verified": bool(r["verified"]),
                    "trust": trust,
                    "status": (
                        "active"
                        if trust >= 80
                        else "pending" if trust >= 50 else "expired"
                    ),
                    "date": str(r["updated_at"])[:10] if r["updated_at"] else "—",
                    "versions": r["versions"] or 1,
                    "conflict": r["field"] in conflict_fields,
                }
            )
        return result

    except Exception:
        return []


def _load_metrics(entries: list[dict]) -> dict:
    summary = _qe.system_summary()
    conflicts = sum(1 for e in entries if e["conflict"])
    verified = sum(1 for e in entries if e["verified"])
    dates = [e["date"] for e in entries if e["date"] != "—"]
    return {
        "total": len(entries),
        "verified": verified,
        "trust": f"{summary['trust_score']}%" if summary.get("trust_score") else "—",
        "conflicts": conflicts,
        "last_updated": max(dates) if dates else "—",
    }


# ── Renderers ──────────────────────────────────────────────────────────────


def _render_entry(e: dict) -> None:
    trust = e["trust"]
    trust_color = "#a5d6a7" if trust >= 80 else "#ffcc80" if trust >= 50 else "#ef9a9a"
    verified_badge = f"&nbsp;{badge('✔ VERIFIED', 'active')}" if e["verified"] else ""
    conflict_badge = f"&nbsp;{badge('⚠ CONFLICT', 'conflict')}" if e["conflict"] else ""

    st.markdown(
        f"<div class='nasmi-card'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;'>"
        f"<span style='font-size:0.75rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;'>{e['field']}</span>"
        f"{badge(e['status'].upper(), e['status'])}"
        f"{verified_badge}"
        f"{conflict_badge}"
        f"</div>"
        f"<div style='font-size:1.05rem;font-weight:600;color:#e3f2fd;margin-top:0.3rem;'>"
        f"{e['value']}</div>"
        f"<div style='font-size:0.72rem;color:#37474f;margin-top:0.3rem;'>"
        f"📄 {e['source']} · 📅 {e['date']} · "
        f"🔁 {e['versions']} version{'s' if e['versions'] != 1 else ''}"
        f"</div>"
        f"</div>"
        f"<div style='display:flex;flex-direction:column;align-items:flex-end;gap:0.4rem;'>"
        f"<span style='font-size:0.8rem;color:{trust_color};font-weight:700;'>"
        f"Trust: {trust}%</span>"
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


# ── Load ───────────────────────────────────────────────────────────────────

all_entries = _load_kb()
metrics = _load_metrics(all_entries)

# ── Metrics Bar ────────────────────────────────────────────────────────────

s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Total Entries", metrics["total"])
s2.metric("Verified", metrics["verified"])
s3.metric("Avg Trust", metrics["trust"])
s4.metric("Conflicts", metrics["conflicts"])
s5.metric("Last Updated", metrics["last_updated"])

st.divider()

# ── Controls ───────────────────────────────────────────────────────────────

col_view, col_filter, col_sort, col_search = st.columns([2, 2, 2, 3])

with col_view:
    view = st.selectbox(
        "View",
        ["By Field Type", "By Document", "By Date", "Flat List"],
        label_visibility="collapsed",
    )

with col_filter:
    kb_filter = st.selectbox(
        "Filter",
        ["All", "Verified Only", "Conflicts Only", "Low Trust"],
        label_visibility="collapsed",
    )

with col_sort:
    sort_by = st.selectbox(
        "Sort",
        ["Trust Score ↓", "Date Updated ↓", "Alphabetical"],
        label_visibility="collapsed",
    )

with col_search:
    kb_search = st.text_input(
        "Search KB",
        placeholder="Search by field or value...",
        label_visibility="collapsed",
    )

st.divider()

# ── Filter ─────────────────────────────────────────────────────────────────

filtered = list(all_entries)

if kb_filter == "Verified Only":
    filtered = [e for e in filtered if e["verified"]]
elif kb_filter == "Conflicts Only":
    filtered = [e for e in filtered if e["conflict"]]
elif kb_filter == "Low Trust":
    filtered = [e for e in filtered if e["trust"] < 50]

if kb_search.strip():
    q = kb_search.lower()
    filtered = [
        e
        for e in filtered
        if q in str(e["field"]).lower() or q in str(e["value"]).lower()
    ]

# ── Sort ───────────────────────────────────────────────────────────────────

if sort_by == "Trust Score ↓":
    filtered.sort(key=lambda e: e["trust"], reverse=True)
elif sort_by == "Date Updated ↓":
    filtered.sort(key=lambda e: e["date"], reverse=True)
elif sort_by == "Alphabetical":
    filtered.sort(key=lambda e: str(e["field"]))

# ── Render ─────────────────────────────────────────────────────────────────

if view == "By Field Type":
    field_types = sorted({str(e["field"]) for e in filtered})
    if not field_types:
        _empty_state()
    for ftype in field_types:
        group = [e for e in filtered if e["field"] == ftype]
        with st.expander(f"{ftype}  ({len(group)} entries)", expanded=True):
            for e in group:
                _render_entry(e)

elif view == "Flat List":
    if not filtered:
        _empty_state()
    for e in filtered:
        _render_entry(e)

elif view == "By Document":
    docs = sorted({str(e["source"]) for e in filtered})
    if not docs:
        _empty_state()
    for doc in docs:
        group = [e for e in filtered if e["source"] == doc]
        with st.expander(f"📄 {doc}  ({len(group)} entries)", expanded=False):
            for e in group:
                _render_entry(e)

elif view == "By Date":
    dates = sorted({str(e["date"]) for e in filtered}, reverse=True)
    if not dates:
        _empty_state()
    for d in dates:
        group = [e for e in filtered if e["date"] == d]
        with st.expander(f"📅 {d}  ({len(group)} entries)", expanded=False):
            for e in group:
                _render_entry(e)
