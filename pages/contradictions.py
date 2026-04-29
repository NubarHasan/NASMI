from __future__ import annotations
import streamlit as st
from ui.style import apply_theme, page_header, badge
from db.database import Database
from db.models import ContradictionModel, KnowledgeModel, AuditLogModel
from core.event_bus import bus
from core.events import Event, EventType

apply_theme()
page_header(
    "⚠️",
    "Contradictions",
    "Detected conflicts between extracted values — review and resolve",
)

_con = ContradictionModel()
_km = KnowledgeModel()
_al = AuditLogModel()


# ── Event Notifier ────────────────────────────────────
def _notify(event_type: EventType) -> None:
    bus.publish(Event(event_type=event_type))
    if "sidebar_needs_refresh" in st.session_state:
        st.session_state["sidebar_needs_refresh"] = True


# ── DB Loaders ────────────────────────────────────────
def _load_conflicts() -> list[dict]:
    try:
        with Database() as db:
            rows = db.fetchall(
                """
                SELECT
                    c.id,
                    c.field,
                    c.value_a,
                    c.value_b,
                    c.source_a,
                    c.source_b,
                    c.status,
                    c.created_at,
                    c.resolved_at,
                    da.filename AS file_a,
                    db2.filename AS file_b
                FROM contradictions c
                LEFT JOIN documents da  ON da.id  = c.doc_id_a
                LEFT JOIN documents db2 ON db2.id = c.doc_id_b
                ORDER BY
                    CASE c.status WHEN 'open' THEN 0 ELSE 1 END,
                    c.created_at DESC
                """,
            )
            return [
                {
                    "id": r["id"],
                    "field": r["field"] or "—",
                    "value_a": r["value_a"] or "—",
                    "value_b": r["value_b"] or "—",
                    "source_a": r["file_a"] or r["source_a"] or "—",
                    "source_b": r["file_b"] or r["source_b"] or "—",
                    "date_a": str(r["created_at"] or "—")[:10],
                    "date_b": str(r["resolved_at"] or "—")[:10],
                    "status": r["status"] or "open",
                    "severity": _severity(r["field"]),
                    "note": _note(r["field"], r["source_a"], r["source_b"]),
                }
                for r in rows
            ]
    except Exception:
        return []


def _severity(field: str | None) -> str:
    field = (field or "").lower()
    if any(k in field for k in ("iban", "birth", "passport", "id", "tax")):
        return "high"
    if any(k in field for k in ("address", "phone", "email", "name")):
        return "medium"
    return "low"


def _note(field: str | None, src_a: str | None, src_b: str | None) -> str:
    f = field or "field"
    a = src_a or "?"
    b = src_b or "?"
    return f'Conflict detected for "{f}" between {a} and {b}.'


def _load_stats(items: list[dict]) -> dict:
    return {
        "total": len(items),
        "high": sum(1 for c in items if c["severity"] == "high"),
        "unresolved": sum(1 for c in items if c["status"] == "open"),
        "resolved": sum(1 for c in items if c["status"] != "open"),
    }


# ── DB Actions ────────────────────────────────────────
def _keep(item: dict, value: str, label: str) -> None:
    with Database() as db:
        _con.resolve(db, int(item["id"]), f"accepted:{label}")
        _km.upsert(db, str(item["field"]), value, 1.0, str(item[f"source_{label}"]))
        _al.log(db, f"keep_{label}", "contradictions", int(item["id"]), "user", value)
    _notify(EventType.CONFLICT_DETECTED)


def _save_manual(item: dict, value: str) -> None:
    with Database() as db:
        _con.resolve(db, int(item["id"]), "manual")
        _km.upsert(db, str(item["field"]), value, 1.0, "manual")
        _al.log(db, "manual", "contradictions", int(item["id"]), "user", value)
    _notify(EventType.CONFLICT_DETECTED)


def _skip(item: dict) -> None:
    with Database() as db:
        _con.resolve(db, int(item["id"]), "skipped")
        _al.log(db, "skip", "contradictions", int(item["id"]), "user", "")
    _notify(EventType.CONFLICT_DETECTED)


# ── Renderers ─────────────────────────────────────────
def _render_conflict(c: dict) -> None:
    severity = str(c["severity"])
    severity_color = (
        "#ef9a9a"
        if severity == "high"
        else "#ffcc80" if severity == "medium" else "#90a4ae"
    )
    status_resolved = c["status"] != "open"
    opacity = "0.5" if status_resolved else "1"

    st.markdown(
        f"<div class='nasmi-card' style='border-left:3px solid {severity_color};"
        f"opacity:{opacity};'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;'>"
        f"<span style='font-weight:700;color:#e3f2fd;font-size:0.95rem;'>{c['field']}</span>"
        f"{badge(severity.upper(), 'conflict')}"
        f"{badge(str(c['status']).upper(), 'active' if status_resolved else 'pending')}"
        f"</div>"
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;margin-top:0.3rem;'>"
        f"<div style='background:#0d1b2a;border-radius:6px;padding:0.6rem;'>"
        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;margin-bottom:0.2rem;'>Value A</div>"
        f"<div style='font-size:0.9rem;font-weight:600;color:#e3f2fd;'>{c['value_a']}</div>"
        f"<div style='font-size:0.7rem;color:#37474f;margin-top:0.2rem;'>"
        f"📄 {c['source_a']} · 📅 {c['date_a']}</div>"
        f"</div>"
        f"<div style='background:#0d1b2a;border-radius:6px;padding:0.6rem;'>"
        f"<div style='font-size:0.7rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;margin-bottom:0.2rem;'>Value B</div>"
        f"<div style='font-size:0.9rem;font-weight:600;color:#e3f2fd;'>{c['value_b']}</div>"
        f"<div style='font-size:0.7rem;color:#37474f;margin-top:0.2rem;'>"
        f"📄 {c['source_b']} · 📅 {c['date_b']}</div>"
        f"</div>"
        f"</div>"
        f"<div style='font-size:0.75rem;color:#546e7a;margin-top:0.5rem;'>"
        f"🔍 {c['note']}"
        f"</div>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_actions(c: dict, unique_key: str) -> None:
    if c["status"] != "open":
        st.markdown(
            "<div style='font-size:0.75rem;color:#37474f;"
            "padding:0.3rem 0;'>✅ Already resolved</div>",
            unsafe_allow_html=True,
        )
        return

    col_a, col_b, col_skip, col_manual = st.columns([2, 2, 1, 2])

    with col_a:
        if st.button("✅ Keep A", key=f"keep_a_{unique_key}", use_container_width=True):
            _keep(c, str(c["value_a"]), "a")
            st.toast(f"Kept A: {c['value_a']}", icon="✅")
            st.rerun()

    with col_b:
        if st.button("✅ Keep B", key=f"keep_b_{unique_key}", use_container_width=True):
            _keep(c, str(c["value_b"]), "b")
            st.toast(f"Kept B: {c['value_b']}", icon="✅")
            st.rerun()

    with col_skip:
        if st.button("⏭", key=f"skip_{unique_key}", use_container_width=True):
            _skip(c)
            st.toast("Skipped", icon="⏭")
            st.rerun()

    with col_manual:
        if st.button(
            "✏️ Enter Manually", key=f"manual_{unique_key}", use_container_width=True
        ):
            st.session_state[f"manual_open_{unique_key}"] = True

    if st.session_state.get(f"manual_open_{unique_key}"):
        manual_val = st.text_input(
            "Manual value",
            placeholder=f"Enter correct value for {c['field']}...",
            key=f"manual_val_{unique_key}",
        )
        if st.button("💾 Save", key=f"save_manual_{unique_key}"):
            if manual_val.strip():
                _save_manual(c, manual_val.strip())
                st.toast(f"Saved: {manual_val}", icon="💾")
                st.session_state[f"manual_open_{unique_key}"] = False
                st.rerun()
            else:
                st.warning("Value cannot be empty.")


def _empty_state(msg: str = "No conflicts found.") -> None:
    st.markdown(
        f"<div class='nasmi-card' style='text-align:center;padding:3rem;"
        f"color:#37474f;'>{msg}</div>",
        unsafe_allow_html=True,
    )


# ── Controls ──────────────────────────────────────────
col_sev, col_status, col_search = st.columns([2, 2, 4])

with col_sev:
    sev_filter = st.selectbox(
        "Severity",
        ["All", "high", "medium", "low"],
        label_visibility="collapsed",
        key="con_sev",
    )

with col_status:
    status_filter = st.selectbox(
        "Status",
        ["All", "open", "resolved", "skipped", "manual"],
        label_visibility="collapsed",
        key="con_status",
    )

with col_search:
    con_search = st.text_input(
        "Search conflicts",
        placeholder="Search by field, source, value...",
        label_visibility="collapsed",
        key="con_search",
    )

st.divider()

# ── Load Data ─────────────────────────────────────────
all_conflicts = _load_conflicts()
stats = _load_stats(all_conflicts)

# ── Stats ─────────────────────────────────────────────
s1, s2, s3, s4 = st.columns(4)
s1.metric("Total Conflicts", stats["total"])
s2.metric("High Severity", stats["high"])
s3.metric("Unresolved", stats["unresolved"])
s4.metric("Resolved", stats["resolved"])

st.divider()

# ── Filter ────────────────────────────────────────────
filtered = list(all_conflicts)

if sev_filter != "All":
    filtered = [c for c in filtered if c["severity"] == sev_filter]

if status_filter != "All":
    filtered = [c for c in filtered if c["status"] == status_filter]

if con_search.strip():
    q = con_search.lower()
    filtered = [
        c
        for c in filtered
        if q in str(c["field"]).lower()
        or q in str(c["value_a"]).lower()
        or q in str(c["value_b"]).lower()
        or q in str(c["source_a"]).lower()
        or q in str(c["source_b"]).lower()
    ]

# ── Render ────────────────────────────────────────────
if not filtered:
    _empty_state("No conflicts match the current filter. ✅")
else:
    for c in filtered:
        unique_key = str(c["id"])
        _render_conflict(c)
        _render_actions(c, unique_key)
        st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)
