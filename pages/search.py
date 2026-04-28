import streamlit as st
from ui.style import apply_theme, page_header, badge
from db.database import Database
from llm.ollama_client import OllamaClient  # type: ignore[attr-defined]


apply_theme()
page_header(
    "🔍",
    "Search & Query",
    "Search across documents · entities · knowledge — powered by NER + LLM",
)

_ollama = OllamaClient()

for _k, _v in [
    ("search_query", ""),
    ("search_results", []),
    ("search_mode", "Smart Search"),
    ("llm_answer", ""),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


def _search_smart(query: str, filters: dict) -> list:
    results: list[dict[str, int | str]] = []
    with Database() as db:
        rows = db.fetchall(
            """
            SELECT e.id, e.entity_type, e.entity_value, e.confidence, e.source,
                   e.created_at, d.filename, d.file_type
            FROM entities e
            LEFT JOIN documents d ON d.id = e.document_id
            WHERE e.entity_value LIKE ?
            ORDER BY e.confidence DESC
            LIMIT 50
            """,
            (f"%{query}%",),
        )
        for r in rows:
            results.append(
                {
                    "entity": str(r["entity_type"] or ""),
                    "value": str(r["entity_value"] or "—"),
                    "entity_type": str(r["entity_type"] or ""),
                    "source_doc": str(r["filename"] or "—"),
                    "doc_type": str(r["file_type"] or "—"),
                    "confidence": int(float(r["confidence"] or 0) * 100),
                    "status": "active",
                    "date_added": str(r["created_at"] or "—"),
                }
            )

        k_rows = db.fetchall(
            "SELECT field, value, confidence, source, updated_at FROM knowledge WHERE value LIKE ? LIMIT 20",
            (f"%{query}%",),
        )
        for r in k_rows:
            results.append(
                {
                    "entity": str(r["field"] or ""),
                    "value": str(r["value"] or "—"),
                    "entity_type": "KNOWLEDGE",
                    "source_doc": str(r["source"] or "—"),
                    "doc_type": "Knowledge Base",
                    "confidence": int(float(r["confidence"] or 0) * 100),
                    "status": "new",
                    "date_added": str(r["updated_at"] or "—"),
                }
            )

    results.sort(key=lambda x: int(x["confidence"]), reverse=True)
    return results


def _search_exact(query: str, filters: dict) -> list:
    results: list[dict[str, int | str]] = []
    with Database() as db:
        rows = db.fetchall(
            """
            SELECT e.id, e.entity_type, e.entity_value, e.confidence, e.source,
                   e.created_at, d.filename, d.file_type
            FROM entities e
            LEFT JOIN documents d ON d.id = e.document_id
            WHERE e.entity_value = ?
            ORDER BY e.confidence DESC
            """,
            (query,),
        )
        for r in rows:
            results.append(
                {
                    "entity": str(r["entity_type"] or ""),
                    "value": str(r["entity_value"] or "—"),
                    "entity_type": str(r["entity_type"] or ""),
                    "source_doc": str(r["filename"] or "—"),
                    "doc_type": str(r["file_type"] or "—"),
                    "confidence": int(float(r["confidence"] or 0) * 100),
                    "status": "active",
                    "date_added": str(r["created_at"] or "—"),
                }
            )
    return results


def _search_entity_lookup(query: str, filters: dict) -> list:
    results: list = []
    entity_type = str(filters.get("entity_type", "All"))
    with Database() as db:
        if entity_type != "All":
            rows = db.fetchall(
                """
                SELECT e.id, e.entity_type, e.entity_value, e.confidence, e.source,
                       e.created_at, d.filename, d.file_type
                FROM entities e
                LEFT JOIN documents d ON d.id = e.document_id
                WHERE e.entity_type = ? AND e.entity_value LIKE ?
                ORDER BY e.confidence DESC LIMIT 50
                """,
                (entity_type, f"%{query}%"),
            )
        else:
            rows = db.fetchall(
                """
                SELECT e.id, e.entity_type, e.entity_value, e.confidence, e.source,
                       e.created_at, d.filename, d.file_type
                FROM entities e
                LEFT JOIN documents d ON d.id = e.document_id
                WHERE e.entity_value LIKE ?
                ORDER BY e.confidence DESC LIMIT 50
                """,
                (f"%{query}%",),
            )
        for r in rows:
            results.append(
                {
                    "entity": str(r["entity_type"] or ""),
                    "value": str(r["entity_value"] or "—"),
                    "entity_type": str(r["entity_type"] or ""),
                    "source_doc": str(r["filename"] or "—"),
                    "doc_type": str(r["file_type"] or "—"),
                    "confidence": int(float(r["confidence"] or 0) * 100),
                    "status": "active",
                    "date_added": str(r["created_at"] or "—"),
                }
            )
    return results


def _search_semantic(query: str) -> tuple[list, str]:
    with Database() as db:
        k_rows = db.fetchall("SELECT field, value, source FROM knowledge LIMIT 40")
        e_rows = db.fetchall(
            "SELECT entity_type, entity_value, source FROM entities ORDER BY confidence DESC LIMIT 40"
        )

    context_parts = ["=== Knowledge Base ==="]
    for r in k_rows:
        context_parts.append(f'{r["field"]}: {r["value"]} (source: {r["source"]})')
    context_parts.append("\n=== Extracted Entities ===")
    for r in e_rows:
        context_parts.append(
            f'{r["entity_type"]}: {r["entity_value"]} (source: {r["source"]})'
        )

    context = "\n".join(context_parts)
    system_prompt = (
        "You are NASMI, a personal document intelligence assistant. "
        "Answer questions based ONLY on the provided context. "
        "Be concise, accurate, and structured. "
        "If the answer is not in the context, say so clearly."
    )
    prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"

    try:
        answer = str(_ollama.generate(prompt=prompt, system=system_prompt))
    except Exception as e:
        answer = f"Ollama error: {e}"

    results: list = []
    with Database() as db:
        rows = db.fetchall(
            """
            SELECT e.entity_type, e.entity_value, e.confidence, e.source,
                   e.created_at, d.filename, d.file_type
            FROM entities e
            LEFT JOIN documents d ON d.id = e.document_id
            WHERE e.entity_value LIKE ?
            ORDER BY e.confidence DESC LIMIT 20
            """,
            (f"%{query}%",),
        )
        for r in rows:
            results.append(
                {
                    "entity": str(r["entity_type"] or ""),
                    "value": str(r["entity_value"] or "—"),
                    "entity_type": str(r["entity_type"] or ""),
                    "source_doc": str(r["filename"] or "—"),
                    "doc_type": str(r["file_type"] or "—"),
                    "confidence": int(float(r["confidence"] or 0) * 100),
                    "status": "active",
                    "date_added": str(r["created_at"] or "—"),
                }
            )

    return results, answer


def _quick_search(q: str) -> None:
    st.session_state.search_query = q
    st.rerun()


def _result_card(r: dict) -> None:
    conf = int(r["confidence"])
    conf_color = "#a5d6a7" if conf >= 80 else "#ffcc80" if conf >= 50 else "#ef9a9a"
    st.markdown(
        f"<div class='nasmi-card'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div>"
        f"<div style='font-size:0.75rem;color:#546e7a;text-transform:uppercase;"
        f"letter-spacing:0.5px;'>{r['entity']}</div>"
        f"<div style='font-size:1.1rem;font-weight:600;color:#e3f2fd;margin-top:0.2rem;'>"
        f"{r['value']}</div>"
        f"<div style='font-size:0.75rem;color:#37474f;margin-top:0.3rem;'>"
        f"📄 {r['source_doc']} · {r['doc_type']} · Added: {r['date_added']}"
        f"</div>"
        f"</div>"
        f"<div style='display:flex;flex-direction:column;align-items:flex-end;gap:0.3rem;'>"
        f"{badge(str(r['entity_type']), str(r['status']))}"
        f"<span style='font-size:0.72rem;color:{conf_color};'>"
        f"Confidence: {conf}%</span>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Search Bar ────────────────────────────────────────
col_input, col_mode, col_btn = st.columns([4, 2, 1])

with col_input:
    query = st.text_input(
        "Search",
        placeholder='e.g. "What is my IBAN?" · "Show all expired documents" · "Find address"',
        label_visibility="collapsed",
        value=st.session_state.search_query,
        key="search_input",
    )

with col_mode:
    mode = st.selectbox(
        "Mode",
        ["Smart Search", "Exact Match", "Semantic (LLM)", "Entity Lookup"],
        label_visibility="collapsed",
    )

with col_btn:
    search_btn = st.button("🔍 Search", use_container_width=True)

mode_map = {
    "Smart Search": ("new", "Combines keyword + entity + semantic search"),
    "Exact Match": ("active", "Searches for exact text across all documents"),
    "Semantic (LLM)": (
        "pending",
        "Uses Ollama LLM to understand intent — slower but smarter",
    ),
    "Entity Lookup": ("new", "Searches by entity type: PERSON · DATE · ADDRESS · ID"),
}
m_status, m_desc = mode_map[str(mode)]
st.markdown(
    f"<div style='margin-bottom:0.8rem;display:flex;align-items:center;gap:0.6rem;'>"
    f"{badge(str(mode), m_status)}"
    f"<span style='font-size:0.78rem;color:#546e7a;'>{m_desc}</span>"
    f"</div>",
    unsafe_allow_html=True,
)

st.divider()

# ── Filters ───────────────────────────────────────────
with st.expander("🎛️ Advanced Filters", expanded=False):
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        filter_entity = st.selectbox(
            "Entity Type", ["All", "PERSON", "DATE", "ADDRESS", "ID", "FINANCE", "GPE"]
        )
    with fc2:
        filter_doc = st.selectbox(
            "Document Type",
            ["All", "Personalausweis", "Reisepass", "Lohnabrechnung", "Other"],
        )
    with fc3:
        filter_status = st.selectbox(
            "Status", ["All", "Active", "Expired", "Pending", "Conflict"]
        )
    with fc4:
        filter_sort = st.selectbox(
            "Sort By", ["Relevance", "Date Added", "Confidence", "Document Type"]
        )

filters = {
    "entity_type": str(filter_entity),
    "doc_type": str(filter_doc),
    "status": str(filter_status),
    "sort_by": str(filter_sort),
}

# ── Run Search ────────────────────────────────────────
query_str = str(query or "").strip()

if search_btn and query_str:
    st.session_state.search_query = query_str
    st.session_state.llm_answer = ""

    st.markdown(
        f"<div style='font-size:0.8rem;color:#546e7a;margin-bottom:0.8rem;'>"
        f"Searching for: <span style='color:#4fc3f7;font-weight:600;'>'{query_str}'</span> "
        f"using <span style='color:#4fc3f7;'>{mode}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    with st.spinner("Searching..."):
        if mode == "Smart Search":
            results = _search_smart(query_str, filters)
        elif mode == "Exact Match":
            results = _search_exact(query_str, filters)
        elif mode == "Entity Lookup":
            results = _search_entity_lookup(query_str, filters)
        else:
            results, llm_answer = _search_semantic(query_str)
            st.session_state.llm_answer = llm_answer

    st.session_state.search_results = results

    if mode == "Semantic (LLM)" and st.session_state.llm_answer:
        st.markdown("#### 🤖 LLM Answer")
        st.markdown(
            f"<div class='nasmi-card' style='border-left:3px solid #1565c0;"
            f"padding:1rem 1.2rem;color:#e3f2fd;font-size:0.9rem;line-height:1.6;'>"
            f"{st.session_state.llm_answer}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.divider()

    st.markdown(f"#### 📋 Results ({len(results)} found)")

    if results:
        for r in results:
            _result_card(r)
    else:
        st.markdown(
            "<div class='nasmi-card' style='text-align:center;padding:2rem;color:#546e7a;'>"
            "No results found. Try a different query or mode."
            "</div>",
            unsafe_allow_html=True,
        )

elif search_btn and not query_str:
    st.warning("Please enter a search query.")

else:
    st.markdown(
        "<div class='nasmi-card' style='text-align:center;padding:4rem 1rem;"
        "color:#37474f;border:2px dashed #1e2d4a;'>"
        "<div style='font-size:2.5rem;'>🔍</div>"
        "<div style='margin-top:0.5rem;font-size:0.9rem;'>Start searching your knowledge</div>"
        "<div style='font-size:0.75rem;margin-top:0.4rem;'>"
        "Try: 'What is my address?' · 'Show expired documents' · 'Find IBAN'"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("#### ⚡ Quick Searches")
    qc1, qc2, qc3, qc4 = st.columns(4)
    if qc1.button("🪪 My Identity Fields", use_container_width=True):
        _quick_search("full name")
    if qc2.button("📅 Expiring Documents", use_container_width=True):
        _quick_search("expir")
    if qc3.button("⚠️ Contradictions", use_container_width=True):
        _quick_search("contradiction")
    if qc4.button("💰 Financial Data", use_container_width=True):
        _quick_search("IBAN")
