from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge
from db.database import Database
from db.models import EntityModel, ContradictionModel
from knowledge.quality_engine import QualityEngine

apply_theme()
page_header(
    "🧠",
    "Knowledge Base",
    "All extracted knowledge — entities · values · sources · trust scores",
)

_ent_model = EntityModel()
_con_model = ContradictionModel()
_qe = QualityEngine()


def _load_kb() -> list[dict]:
    try:
        with Database() as db:
            rows = db.fetchall(
                """
                SELECT
                    e.id,
                    e.entity_type,
                    e.entity_value,
                    e.confidence,
                    e.source,
                    e.created_at,
                    d.filename,
                    d.file_type,
                    (
                        SELECT COUNT(*) FROM entities e2
                        WHERE e2.entity_type = e.entity_type
                    ) AS versions
                FROM entities e
                LEFT JOIN documents d ON d.id = e.document_id
                ORDER BY e.created_at DESC
                """,
            )

            conflict_fields: set[str] = set()
            conflicts = db.fetchall("SELECT field FROM contradictions")
            for c in conflicts:
                conflict_fields.add(c["field"])

        result = []
        for r in rows:
            trust = int((r["confidence"] or 0) * 100)
            result.append(
                {
                    "id": r["id"],
                    "entity": r["entity_type"],
                    "value": r["entity_value"] or "—",
                    "type": r["entity_type"],
                    "source": r["filename"] or "—",
                    "doc_type": r["file_type"] or "—",
                    "trust": trust,
                    "confidence": trust,
                    "status": (
                        "active"
                        if trust >= 80
                        else "pending" if trust >= 50 else "expired"
                    ),
                    "date": str(r["created_at"])[:10] if r["created_at"] else "—",
                    "versions": r["versions"] or 1,
                    "conflict": r["entity_type"] in conflict_fields,
                }
            )
        return result

    except Exception:
        return []


def _load_metrics(entries: list[dict]) -> dict:
    summary = _qe.system_summary()
    conflicts = sum(1 for e in entries if e["conflict"])
    dates = [e["date"] for e in entries if e["date"] != "—"]
    last_updated = max(dates) if dates else "—"

    unique = len({e["entity"] for e in entries})

    return {
        "total": len(entries),
        "unique": unique,
        "trust": f"{summary['trust_score']}%" if summary["trust_score"] else "—",
        "conflicts": conflicts,
        "last_updated": last_updated,
    }


def _render_entry(e: dict) -> None:
    trust: int = e["trust"]  # type: ignore
    confidence: int = e["confidence"]  # type: ignore
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


# ── Load Data ─────────────────────────────────────────
all_entries = _load_kb()
metrics = _load_metrics(all_entries)

# ── Metrics Bar ───────────────────────────────────────
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Total Entries", metrics["total"])
s2.metric("Unique Entities", metrics["unique"])
s3.metric("Avg Trust Score", metrics["trust"])
s4.metric("Conflicts", metrics["conflicts"])
s5.metric("Last Updated", metrics["last_updated"])

st.divider()

# ── Controls ──────────────────────────────────────────
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
    sort_by = st.selectbox(
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

# ── Filter ────────────────────────────────────────────
filtered = list(all_entries)

if kb_filter != "All":
    filtered = [e for e in filtered if e["type"] == kb_filter]

if kb_search.strip():
    q = kb_search.lower()
    filtered = [
        e
        for e in filtered
        if q in str(e["entity"]).lower() or q in str(e["value"]).lower()
    ]

# ── Sort ──────────────────────────────────────────────
if sort_by == "Trust Score ↓":
    filtered.sort(key=lambda e: e["trust"], reverse=True)
elif sort_by == "Date Added ↓":
    filtered.sort(key=lambda e: e["date"], reverse=True)
elif sort_by == "Confidence ↓":
    filtered.sort(key=lambda e: e["confidence"], reverse=True)
elif sort_by == "Alphabetical":
    filtered.sort(key=lambda e: str(e["entity"]))

# ── Render ────────────────────────────────────────────
if view == "By Entity Type":
    entity_types = sorted({str(e["type"]) for e in filtered})
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
