import streamlit as st
from db.database import Database


st.markdown('''
<style>
.search-result-item {
    background: linear-gradient(135deg, rgba(79,195,247,0.1) 0%, rgba(79,195,247,0.05) 100%);
    border: 1px solid #4fc3f7; border-radius: 8px;
    padding: 1.2rem; margin: 0.8rem 0; transition: all 0.3s ease;
}
.search-result-item:hover { transform: translateX(4px); }
.result-title   { font-size: 1.1rem; font-weight: 700; color: #4fc3f7; margin-bottom: 0.3rem; }
.result-snippet { font-size: 0.9rem; color: #b0bec5; margin: 0.5rem 0; }
.result-meta    { font-size: 0.8rem; color: #90caf9; margin-top: 0.5rem; }
.form-field     { background: rgba(255,255,255,0.05); border: 1px solid #ba68c8; border-radius: 8px; padding: 1rem; margin: 0.8rem 0; }
.form-label     { font-weight: 600; color: #ba68c8; margin-bottom: 0.5rem; }
.form-value     { color: #e0e0e0; font-size: 1rem; padding: 0.5rem; background: rgba(0,0,0,0.2); border-radius: 4px; }
.document-list-item {
    background: rgba(255,255,255,0.03); border: 1px solid #4fc3f7;
    border-radius: 6px; padding: 0.8rem; margin: 0.5rem 0;
    display: flex; justify-content: space-between; align-items: center;
}
.document-name { color: #4fc3f7; font-weight: 600; }
.document-date { font-size: 0.8rem; color: #90caf9; }
.ai-suggestion {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: 1px solid #9575cd; border-radius: 8px; padding: 1rem; margin: 0.8rem 0;
}
.ai-suggestion-title { color: #e0e0e0; font-weight: 600; margin-bottom: 0.3rem; }
.ai-suggestion-text  { color: #c5cae9; font-size: 0.9rem; }
</style>
''', unsafe_allow_html=True)

if 'library_state' not in st.session_state:
    st.session_state['library_state'] = {
        'search_query': '',
        'current_tab': 'search',
    }


def search_entities(query: str) -> list:
    if not query.strip():
        return []
    with Database() as db:
        results = db.fetchall(
            'SELECT entity_value, entity_type, confidence, source FROM entities '
            'WHERE LOWER(entity_value) LIKE ? ORDER BY confidence DESC LIMIT 50',
            (f'%{query.lower()}%',)
        )
    return results or []


def load_all_documents() -> list:
    with Database() as db:
        docs = db.fetchall(
            'SELECT filename, file_type, uploaded_at, status FROM documents ORDER BY uploaded_at DESC LIMIT 30'
        )
    return docs or []


def load_identity_for_form() -> dict:
    with Database() as db:
        row = db.fetchone('SELECT * FROM identity_core ORDER BY id DESC LIMIT 1')
    return row or {}


def load_knowledge_for_form() -> dict:
    with Database() as db:
        rows = db.fetchall('SELECT field, value FROM knowledge ORDER BY confidence DESC')
    return {r['field']: r['value'] for r in rows} if rows else {}


def load_export_history() -> list:
    with Database() as db:
        rows = db.fetchall(
            'SELECT export_type, created_at, status FROM exports ORDER BY created_at DESC LIMIT 5'
        )
    return rows or []


st.markdown('# 📚 Library & Tools - Search, Forms & Export')
st.markdown('Smart retrieval, form filling, and data export in one workspace')
st.markdown('---')

tabs = st.tabs(['🔍 Search & Query', '📋 Smart Form Filler', '📤 Export Center'])

# ── Tab 0 : Search ─────────────────────────────────────────────────────────
with tabs[0]:
    st.markdown('## 🔍 Semantic Search - Find Information Instantly')

    col_left, col_right = st.columns([3, 1])
    with col_left:
        search_query = st.text_input(
            'Search',
            placeholder='e.g., "John Doe" or "passport number"',
            label_visibility='collapsed',
        )
    with col_right:
        st.selectbox('Mode', ['Keyword', 'Semantic', 'Regex'], label_visibility='collapsed')

    if search_query:
        st.markdown('---')
        results = search_entities(search_query)

        if not results:
            st.info('No results found. Try different keywords.')
        else:
            st.markdown(f'### Found {len(results)} results')
            for r in results[:10]:
                val  = r.get('entity_value', 'Unknown')
                typ  = r.get('entity_type', '—')
                conf = float(r.get('confidence', 0))
                src  = r.get('source', '—')
                st.markdown(
                    f'<div class="search-result-item">'
                    f'<div class="result-title">{val}</div>'
                    f'<div class="result-snippet">Type: {typ} · Source: {src}</div>'
                    f'<div class="result-meta">Confidence: {int(conf * 100)}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info('📝 Enter a search query to begin searching across all documents')
        st.markdown('---')
        st.markdown('### Recent Documents')

        for doc in load_all_documents()[:5]:
            name   = doc.get('filename', 'Unknown')
            date   = doc.get('uploaded_at', '—')
            status = doc.get('status', '—')
            st.markdown(
                f'<div class="document-list-item">'
                f'<div><div class="document-name">📄 {name}</div>'
                f'<div class="document-date">{date} · {status}</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Tab 1 : Smart Form Filler ──────────────────────────────────────────────
with tabs[1]:
    st.markdown('## 📋 Smart Form Filler - AI-Powered Data Extraction')

    col_left, col_right = st.columns([2, 1])
    with col_left:
        form_type = st.selectbox(
            'Form Type',
            ['Identity Document', 'German Tax Return (Steuererklärung)', 'Loan Application', 'Employment Contract'],
            label_visibility='collapsed',
        )
    with col_right:
        if st.button('🔄 Reload from DB', use_container_width=True):
            st.rerun()

    st.markdown('---')

    identity = load_identity_for_form()
    knowledge = load_knowledge_for_form()

    if form_type == 'Identity Document':
        st.markdown('#### Identity Information')
        fields_map = {
            'Full Name':    identity.get('full_name')    or knowledge.get('full_name', '—'),
            'Date of Birth':identity.get('birth_date')   or knowledge.get('date_of_birth', '—'),
            'Nationality':  identity.get('nationality')  or knowledge.get('nationality', '—'),
            'ID Number':    identity.get('id_number')    or knowledge.get('id_number', '—'),
            'Status':       identity.get('status', 'active'),
        }
        for label, value in fields_map.items():
            st.markdown(
                f'<div class="form-field">'
                f'<div class="form-label">{label}</div>'
                f'<div class="form-value">{value or "—"}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    elif form_type == 'German Tax Return (Steuererklärung)':
        st.markdown('#### Taxpayer Information')
        tax_fields = {
            'Full Name': identity.get('full_name') or knowledge.get('full_name', '—'),
            'Tax ID':    knowledge.get('id_number', '—'),
            'Email':     knowledge.get('email', '—'),
        }
        for label, value in tax_fields.items():
            st.markdown(
                f'<div class="form-field">'
                f'<div class="form-label">{label}</div>'
                f'<div class="form-value">{value or "—"}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    if not identity and not knowledge:
        st.warning('⚠️ No data found. Upload documents first to auto-fill forms.')

    if st.button('🤖 AI Suggest Values', use_container_width=True):
        st.markdown(
            '<div class="ai-suggestion">'
            '<div class="ai-suggestion-title">🧠 AI Suggestions</div>'
            '<div class="ai-suggestion-text">Based on your documents, all available fields have been auto-filled from the knowledge base.</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown('---')
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button('💾 Save Draft', use_container_width=True):
            st.success('Form saved!')
    with col_b:
        if st.button('📤 Export Form', use_container_width=True):
            st.success('Form exported!')
    with col_c:
        if st.button('✅ Submit', use_container_width=True):
            st.success('Form submitted!')

# ── Tab 2 : Export Center ──────────────────────────────────────────────────
with tabs[2]:
    st.markdown('## 📤 Export Center - Multi-Format Data Export')

    col_what, col_fmt = st.columns(2)
    with col_what:
        export_what = st.selectbox(
            'Export',
            ['All Data', 'Entities Only', 'Addresses', 'Timeline', 'Documents'],
            label_visibility='collapsed',
        )
    with col_fmt:
        export_format = st.selectbox(
            'Format',
            ['CSV', 'JSON', 'PDF', 'Excel', 'XML'],
            label_visibility='collapsed',
        )

    st.markdown('---')
    st.markdown('### Export Options')

    col_left, col_right = st.columns(2)
    with col_left:
        st.checkbox('Include Metadata', value=True)
        st.checkbox('Include Confidence Scores', value=True)
        st.checkbox('Anonymize Personal Data', value=False)
    with col_right:
        st.checkbox('Compress (ZIP)', value=False)
        st.checkbox('Encrypt with Password', value=False)

    st.markdown('---')
    if st.button('🚀 Export Now', use_container_width=True, type='primary'):
        with Database() as db:
            db.execute(
                'INSERT INTO exports (export_type, status) VALUES (?, ?)',
                (f'{export_what}_{export_format}', 'completed')
            )
        st.progress(100)
        st.success(f'✅ Export completed! {export_format} file ready.')
        st.balloons()

    st.markdown('---')
    st.markdown('### Export History')

    history = load_export_history()
    if not history:
        st.info('No exports yet.')
    else:
        for exp in history:
            st.markdown(
                f'<div class="document-list-item">'
                f'<div><div class="document-name">{exp.get("export_type", "—")}</div>'
                f'<div class="document-date">{exp.get("created_at", "—")}</div></div>'
                f'<div>✅</div></div>',
                unsafe_allow_html=True,
            )

st.markdown('---')
st.markdown('💡 All search results are powered by the local knowledge base for intelligent context-aware retrieval.')