from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge
from db.database import Database
from db.models import (
    ReviewQueueModel,
    ContradictionModel,
    KnowledgeModel,
    AuditLogModel,
)

apply_theme()
page_header(
    "✋",
    "Review Queue",
    "Human-in-the-loop validation — Critical · Suspicious · Low Risk",
)

_rq = ReviewQueueModel()
_con = ContradictionModel()
_km = KnowledgeModel()
_al = AuditLogModel()

PRIORITY_MAP = {2: "critical", 1: "suspicious", 0: "low"}
PRIORITY_NUM = {"critical": 2, "suspicious": 1, "low": 0}


# ── DB Loaders ────────────────────────────────────────
def _load_queue() -> list[dict]:
    items: list[dict] = []
    try:
        with Database() as db:
            rq_rows = db.fetchall(
                """
                SELECT
                    rq.id,
                    rq.entity_id,
                    rq.field,
                    rq.value,
                    rq.priority,
                    rq.created_at,
                    e.entity_type,
                    e.confidence,
                    d.filename,
                    k.value AS known_value,
                    k.updated_at AS last_updated
                FROM review_queue rq
                LEFT JOIN entities   e ON e.id  = rq.entity_id
                LEFT JOIN documents  d ON d.id  = e.document_id
                LEFT JOIN knowledge  k ON k.field = rq.field
                WHERE rq.status = ?
                ORDER BY rq.priority DESC, rq.created_at ASC
                """,
                ("pending",),
            )
            for r in rq_rows:
                pri_num = int(r["priority"] or 0)
                items.append(
                    {
                        "id": r["id"],
                        "entity_id": r["entity_id"],
                        "field": r["field"] or "—",
                        "value": r["value"] or "—",
                        "known_value": r["known_value"] or "—",
                        "type": r["entity_type"] or "OTHER",
                        "source": r["filename"] or "—",
                        "confidence": int((r["confidence"] or 0) * 100),
                        "priority": PRIORITY_MAP.get(pri_num, "low"),
                        "priority_num": pri_num,
                        "status": "pending",
                        "last_updated": str(r["last_updated"] or "—")[:10],
                        "reason": _reason(PRIORITY_MAP.get(pri_num, "low")),
                        "source_type": "queue",
                    }
                )

            con_rows = db.fetchall(
                """
                SELECT id, field, value_a, value_b, source_a, source_b
                FROM contradictions
                WHERE status = ?
                ORDER BY id ASC
                """,
                ("open",),
            )
            for c in con_rows:
                items.append(
                    {
                        "id": c["id"],
                        "entity_id": None,
                        "field": c["field"] or "—",
                        "value": c["value_a"] or "—",
                        "known_value": c["value_b"] or "—",
                        "type": "CONFLICT",
                        "source": c["source_a"] or "—",
                        "confidence": 0,
                        "priority": "critical",
                        "priority_num": 2,
                        "status": "pending",
                        "last_updated": "—",
                        "reason": f"Conflict detected — value_b from: {c['source_b'] or '?'}",
                        "source_type": "contradiction",
                    }
                )
    except Exception:
        pass
    return items


def _reason(priority: str) -> str:
    return {
        "critical": "Frozen field — manual review required before any update.",
        "suspicious": "Low confidence or partial match — extraction may be inaccurate.",
        "low": "New field — no existing value to compare against.",
    }.get(priority, "—")


def _load_stats(items: list[dict]) -> dict:
    with Database() as db:
        today_count = db.fetchone(
            "SELECT COUNT(*) AS c FROM review_queue WHERE status != 'pending' AND DATE(resolved_at) = DATE('now')",
        )
    return {
        "total": len(items),
        "critical": sum(1 for i in items if i["priority"] == "critical"),
        "suspicious": sum(1 for i in items if i["priority"] == "suspicious"),
        "low": sum(1 for i in items if i["priority"] == "low"),
        "today": int((today_count or {}).get("c", 0)),  # type: ignore[arg-type]
    }


# ── DB Actions ────────────────────────────────────────
def _accept(item: dict, value: str) -> None:
    with Database() as db:
        if item["source_type"] == "contradiction":
            _con.resolve(db, int(item["id"]), f"accepted:{value}")
        else:
            _rq.resolve(db, int(item["id"]), "approved")
        _km.upsert(db, str(item["field"]), value, 1.0, str(item["source"]))
        _al.log(db, "accept", "review_queue", int(item["id"]), "user", value)


def _reject(item: dict) -> None:
    with Database() as db:
        if item["source_type"] == "contradiction":
            _con.resolve(db, int(item["id"]), "rejected")
        else:
            _rq.resolve(db, int(item["id"]), "rejected")
        _al.log(db, "reject", "review_queue", int(item["id"]), "user", "")


def _accept_all_low(items: list[dict]) -> int:
    low = [i for i in items if i["priority"] == "low"]
    for item in low:
        _accept(item, str(item["value"]))
    return len(low)


# ── Renderers ─────────────────────────────────────────
def _render_item(item: dict, unique_key: str) -> None:
    priority = str(item["priority"])
    priority_color = (
        "#ef9a9a"
        if priority == "critical"
        else "#ffcc80" if priority == "suspicious" else "#90a4ae"
    )
    conflict_badge = (
        f"&nbsp;{badge('⚠ CONFLICT', 'conflict')}"
        if item["source_type"] == "contradiction"
        else ""
    )

    st.markdown(
        f"<div class='nasmi-card' style='border-left:3px solid {priority_color};'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;'>"
        f"<span style='font-weight:700;color:#e3f2fd;font-size:0.95rem;'>{item['field']}</span>"
        f"{badge(priority.upper(), 'conflict' if priority == 'critical' else 'pending')}"
        f"{badge(str(item['type']), str(item['status']))}"
        f"{conflict_badge}"
        f"</div>"
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;margin:0.4rem 0;'>"
        f"<div style='background:#0d1b2a;border-radius:6px;padding:0.6rem;'>"
        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;margin-bottom:0.2rem;'>Extracted Value</div>"
        f"<div style='font-size:0.9rem;font-weight:600;color:#e3f2fd;'>{item['value']}</div>"
        f"<div style='font-size:0.7rem;color:#37474f;margin-top:0.2rem;'>"
        f"📄 {item['source']} · 🔍 OCR: {item['confidence']}%</div>"
        f"</div>"
        f"<div style='background:#0d1b2a;border-radius:6px;padding:0.6rem;'>"
        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;margin-bottom:0.2rem;'>Current Known Value</div>"
        f"<div style='font-size:0.9rem;font-weight:600;color:#90a4ae;'>{item['known_value']}</div>"
        f"<div style='font-size:0.7rem;color:#37474f;margin-top:0.2rem;'>"
        f"📅 Last updated: {item['last_updated']}</div>"
        f"</div>"
        f"</div>"
        f"<div style='font-size:0.75rem;color:#546e7a;margin-top:0.2rem;'>"
        f"⚠️ {item['reason']}"
        f"</div>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    col_accept, col_edit, col_reject, col_skip = st.columns([2, 2, 2, 1])

    with col_accept:
        if st.button("✅ Accept", key=f"accept_{unique_key}", use_container_width=True):
            _accept(item, str(item["value"]))
            st.toast(f"Accepted: {item['value']}", icon="✅")
            st.rerun()

    with col_edit:
        if st.button(
            "✏️ Edit & Accept", key=f"edit_{unique_key}", use_container_width=True
        ):
            st.session_state[f"edit_open_{unique_key}"] = True

    with col_reject:
        if st.button("❌ Reject", key=f"reject_{unique_key}", use_container_width=True):
            _reject(item)
            st.toast(f"Rejected: {item['field']}", icon="❌")
            st.rerun()

    with col_skip:
        if st.button("⏭", key=f"skip_{unique_key}", use_container_width=True):
            st.toast("Skipped", icon="⏭")

    if st.session_state.get(f"edit_open_{unique_key}"):
        edited = st.text_input(
            "Corrected value",
            value=str(item["value"]),
            key=f"edit_val_{unique_key}",
        )
        if st.button("💾 Save", key=f"save_edit_{unique_key}"):
            if edited.strip():
                _accept(item, edited.strip())
                st.toast(f"Saved: {edited}", icon="💾")
                st.session_state[f"edit_open_{unique_key}"] = False
                st.rerun()
            else:
                st.warning("Value cannot be empty.")

    st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)


def _empty_state(msg: str = "Queue is empty.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:3rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Controls ──────────────────────────────────────────
col_pri, col_type, col_search, col_bulk = st.columns([2, 2, 3, 2])

with col_pri:
    pri_filter = st.selectbox(
        "Priority",
        ["All", "critical", "suspicious", "low"],
        label_visibility="collapsed",
        key="rq_priority",
    )

with col_type:
    type_filter = st.selectbox(
        "Type",
        [
            "All",
            "PERSON",
            "DATE",
            "ADDRESS",
            "ID",
            "FINANCE",
            "GPE",
            "CONFLICT",
            "OTHER",
        ],
        label_visibility="collapsed",
        key="rq_type",
    )

with col_search:
    rq_search = st.text_input(
        "Search queue",
        placeholder="Search by field, value, source...",
        label_visibility="collapsed",
        key="rq_search",
    )

with col_bulk:
    bulk_clicked = st.button("✅ Accept All Low Risk", use_container_width=True)

st.divider()

# ── Load Data ─────────────────────────────────────────
all_items = _load_queue()
stats = _load_stats(all_items)

if bulk_clicked:
    count = _accept_all_low(all_items)
    st.toast(f"Accepted {count} low-risk items", icon="✅")
    st.rerun()

# ── Stats ─────────────────────────────────────────────
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Total Pending", stats["total"])
s2.metric("Critical", stats["critical"])
s3.metric("Suspicious", stats["suspicious"])
s4.metric("Low Risk", stats["low"])
s5.metric("Reviewed Today", stats["today"])

st.divider()

# ── Filter ────────────────────────────────────────────
filtered = list(all_items)

if pri_filter != "All":
    filtered = [i for i in filtered if i["priority"] == pri_filter]

if type_filter != "All":
    filtered = [i for i in filtered if i["type"] == type_filter]

if rq_search.strip():
    q = rq_search.lower()
    filtered = [
        i
        for i in filtered
        if q in str(i["field"]).lower()
        or q in str(i["value"]).lower()
        or q in str(i["source"]).lower()
    ]

# ── Render by Priority ────────────────────────────────
priority_order = ["critical", "suspicious", "low"]
label_map = {
    "critical": "🔴 Critical",
    "suspicious": "🟡 Suspicious",
    "low": "⚪ Low Risk",
}

if not filtered:
    _empty_state("Review queue is empty. ✅ All items have been processed.")
else:
    for pri in priority_order:
        group = [i for i in filtered if i["priority"] == pri]
        if not group:
            continue
        with st.expander(
            f"{label_map[pri]}  ({len(group)} items)", expanded=(pri == "critical")
        ):
            for item in group:
                unique_key = f"{pri}_{str(item['id'])}_{str(item['source_type'])}"
                _render_item(item, unique_key)
