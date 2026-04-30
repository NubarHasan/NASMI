import streamlit as st
from ui.style import apply_theme
from db.database import Database
from core.event_bus import bus
from core.events import Event, EventType
from config import APP

st.set_page_config(
    page_title=f'{APP["name"]} 2.0 - Unified Workspace',
    page_icon='🧠',
    layout='wide',
    initial_sidebar_state='expanded',
)

apply_theme()

st.markdown('''
<style>
.trust-high { 
    background: linear-gradient(135deg, #4caf50 0%, #66bb6a 100%);
    border-left: 4px solid #2e7d32;
    padding: 0.8rem;
    border-radius: 8px;
    color: white;
    font-weight: 600;
}
.trust-medium { 
    background: linear-gradient(135deg, #ffa726 0%, #ffb74d 100%);
    border-left: 4px solid #f57c00;
    padding: 0.8rem;
    border-radius: 8px;
    color: #333;
    font-weight: 600;
}
.trust-low { 
    background: linear-gradient(135deg, #ef5350 0%, #e57373 100%);
    border-left: 4px solid #c62828;
    padding: 0.8rem;
    border-radius: 8px;
    color: white;
    font-weight: 600;
}

.workspace-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
    padding: 1.5rem;
    border-radius: 12px;
    border: 2px solid #4fc3f7;
    margin: 0.5rem 0;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.workspace-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(79, 195, 247, 0.4);
    border-color: #29b6f6;
}
.workspace-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #4fc3f7;
    margin-bottom: 0.5rem;
}
.workspace-desc {
    font-size: 0.85rem;
    color: #b0bec5;
    line-height: 1.4;
}

.ai-assistant {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 60px;
    height: 60px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.5);
    transition: all 0.3s ease;
    z-index: 9999;
}
.ai-assistant:hover {
    transform: scale(1.1) rotate(10deg);
    box-shadow: 0 12px 32px rgba(102, 126, 234, 0.7);
}

.notif-badge {
    position: absolute;
    top: -5px;
    right: -5px;
    background: #ef5350;
    color: white;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: 700;
    border: 2px solid white;
}

.shortcut-hint {
    background: rgba(255,255,255,0.1);
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    color: #90caf9;
    border: 1px solid #64b5f6;
    font-family: 'Courier New', monospace;
}
</style>
''', unsafe_allow_html=True)


def _load_state() -> None:
    with Database() as db:
        doc_row      = db.fetchone('SELECT COUNT(*) as cnt FROM documents')
        review_row   = db.fetchone(
            'SELECT COUNT(*) as cnt FROM review_queue WHERE status = \'pending\''
        )
        conflict_row = db.fetchone(
            'SELECT COUNT(*) as cnt FROM contradictions WHERE status = \'open\''
        )
        trust_row    = db.fetchone('SELECT AVG(confidence) as avg FROM knowledge')
        jobs_row     = db.fetchone(
            'SELECT COUNT(*) as cnt FROM processing_jobs WHERE status = \'running\''
        )
        entities_row  = db.fetchone('SELECT COUNT(DISTINCT entity_value) as cnt FROM entities')
        high_conf_row = db.fetchone(
            'SELECT COUNT(*) as cnt FROM knowledge WHERE confidence >= 0.95'
        )
        low_conf_row  = db.fetchone(
            'SELECT COUNT(*) as cnt FROM knowledge WHERE confidence < 0.7'
        )

    st.session_state['doc_count']      = int(doc_row['cnt'])      if doc_row      else 0
    st.session_state['review_count']   = int(review_row['cnt'])   if review_row   else 0
    st.session_state['conflict_count'] = int(conflict_row['cnt']) if conflict_row else 0
    st.session_state['jobs_running']   = int(jobs_row['cnt'])     if jobs_row     else 0
    st.session_state['entities_count'] = int(entities_row['cnt']) if entities_row else 0
    st.session_state['high_conf_count']= int(high_conf_row['cnt'])if high_conf_row else 0
    st.session_state['low_conf_count'] = int(low_conf_row['cnt']) if low_conf_row  else 0

    trust_val = trust_row['avg'] if trust_row else None
    st.session_state['trust_score'] = float(trust_val or 0)
    st.session_state['trust_label'] = (
        f'{int(float(trust_val or 0) * 100)}%' if trust_val else '—'
    )

    total_items = st.session_state['doc_count']
    if total_items > 0:
        issues       = st.session_state['conflict_count'] + st.session_state['review_count']
        health_score = max(0, 100 - (issues / total_items * 100))
        st.session_state['system_health'] = int(health_score)
    else:
        st.session_state['system_health'] = 100


def _on_state_change(event: Event) -> None:
    _load_state()
    if 'notifications' not in st.session_state:
        st.session_state['notifications'] = []

    notif = {
        'type':      event.event_type.value if hasattr(event, 'event_type') else str(event),
        'message':   f'Event: {event.event_type.value if hasattr(event, "event_type") else str(event)}',
        'timestamp': event.timestamp if hasattr(event, 'timestamp') else '',
    }
    st.session_state['notifications'].insert(0, notif)
    st.session_state['notifications'] = st.session_state['notifications'][:10]


if 'db_initialized' not in st.session_state:
    db = Database()
    db.initialize()
    st.session_state['db_initialized']    = True
    st.session_state['notifications']     = []
    st.session_state['ai_assistant_open'] = False
    st.session_state['current_workspace'] = 'hub'
    _load_state()

    for ev in [
        EventType.DOCUMENT_UPLOADED,
        EventType.ENTITY_VALIDATED,
        EventType.CONFLICT_DETECTED,
        EventType.REVIEW_REQUIRED,
        EventType.ENTITY_MERGED,
    ]:
        bus.subscribe(ev, _on_state_change)

st.session_state.setdefault('system_health',  100)
st.session_state.setdefault('doc_count',       0)
st.session_state.setdefault('review_count',    0)
st.session_state.setdefault('conflict_count',  0)
st.session_state.setdefault('jobs_running',    0)
st.session_state.setdefault('entities_count',  0)
st.session_state.setdefault('high_conf_count', 0)
st.session_state.setdefault('low_conf_count',  0)
st.session_state.setdefault('trust_label',    '—')
st.session_state.setdefault('trust_score',    0.0)

with st.sidebar:
    st.markdown(
        '<div class=\'sidebar-logo\'>'
        '<h1>🧠 NASMI 2.0</h1>'
        '<p style=\'font-size:0.75rem;color:#90caf9;\'>Neural Automated Secure<br>Management of Information</p>'
        '<p style=\'font-size:0.65rem;color:#546e7a;margin-top:0.5rem;\'>✨ Unified Workspace Edition</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    health       = st.session_state['system_health']
    health_color = '#4caf50' if health >= 80 else '#ffa726' if health >= 60 else '#ef5350'
    st.markdown(
        f'<div style=\'text-align:center;padding:1rem;background:rgba(255,255,255,0.05);border-radius:8px;\'>'
        f'<div style=\'font-size:0.7rem;color:#546e7a;\'>SYSTEM HEALTH</div>'
        f'<div style=\'font-size:2rem;font-weight:700;color:{health_color};\'>{health}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            '<div style=\'text-align:center;font-size:0.7rem;color:#546e7a;\'>DOCUMENTS</div>'
            f'<div style=\'text-align:center;font-size:1.3rem;font-weight:700;color:#4fc3f7;\'>{st.session_state["doc_count"]}</div>',
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            '<div style=\'text-align:center;font-size:0.7rem;color:#546e7a;\'>ENTITIES</div>'
            f'<div style=\'text-align:center;font-size:1.3rem;font-weight:700;color:#ba68c8;\'>{st.session_state["entities_count"]}</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown(
            '<div style=\'text-align:center;font-size:0.7rem;color:#546e7a;\'>TRUST SCORE</div>'
            f'<div style=\'text-align:center;font-size:1.3rem;font-weight:700;color:#4fc3f7;\'>{st.session_state["trust_label"]}</div>',
            unsafe_allow_html=True,
        )
    with col_d:
        jobs       = st.session_state['jobs_running']
        jobs_color = '#a5d6a7' if jobs == 0 else '#fff176'
        st.markdown(
            '<div style=\'text-align:center;font-size:0.7rem;color:#546e7a;\'>RUNNING</div>'
            f'<div style=\'text-align:center;font-size:1.3rem;font-weight:700;color:{jobs_color};\'>{jobs}</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    total_alerts = st.session_state['review_count'] + st.session_state['conflict_count']
    if total_alerts > 0:
        st.error(f'⚠️ **{total_alerts} items need attention**')
        if st.session_state['conflict_count'] > 0:
            st.markdown(f'🔴 {st.session_state["conflict_count"]} conflicts')
        if st.session_state['review_count'] > 0:
            st.markdown(f'🟡 {st.session_state["review_count"]} reviews')
    else:
        st.success('✅ All systems operational')

    st.divider()

    st.markdown('**Data Quality:**')
    col_e, col_f = st.columns(2)
    with col_e:
        st.markdown(f'🟢 High: **{st.session_state["high_conf_count"]}**')
    with col_f:
        st.markdown(f'🔴 Low: **{st.session_state["low_conf_count"]}**')

    st.divider()

    if st.button('🔄 Refresh Data', use_container_width=True):
        _load_state()
        st.success('✅ Data refreshed!')
        st.rerun()

    if st.button('🤖 Toggle AI Assistant', use_container_width=True):
        st.session_state['ai_assistant_open'] = not st.session_state['ai_assistant_open']
        st.rerun()

    st.divider()

    if st.session_state.get('notifications'):
        with st.expander('📢 Recent Activity', expanded=False):
            for notif in st.session_state['notifications'][:3]:
                st.markdown(
                    f'<div style=\'font-size:0.7rem;color:#90caf9;margin:0.3rem 0;\'>'
                    f'• {notif["message"]}</div>',
                    unsafe_allow_html=True,
                )

    st.divider()

    st.markdown(
        f'<div style=\'font-size:0.65rem;color:#546e7a;text-align:center;padding-top:1rem;\'>'
        f'NASMI v{APP["version"]} 2.0<br>Local-First · Secure · Unified</div>',
        unsafe_allow_html=True,
    )

workspaces = {
    '🎯 Command Hub': {
        'page':        'pages/hub.py',
        'description': 'Dashboard · Settings · System Overview',
        'shortcut':    'Ctrl+1',
        'modules':     ['Dashboard', 'Settings', 'Logs', 'System Health'],
    },
    '📥 Inbox & Actions': {
        'page':        'pages/inbox.py',
        'description': 'Upload · Review · Resolve Conflicts · Process Documents',
        'shortcut':    'Ctrl+2',
        'modules':     ['Upload', 'Review Queue', 'Contradictions', 'Update Center'],
    },
    '🧠 Knowledge Brain': {
        'page':        'pages/brain.py',
        'description': 'Knowledge Graph · Entities · Timeline · Cognitive Layer',
        'shortcut':    'Ctrl+3',
        'modules':     ['Knowledge Base', 'Address & Field Book', 'Timeline', 'Identity'],
    },
    '📚 Library & Tools': {
        'page':        'pages/library.py',
        'description': 'Search · Smart Forms · Export · Data Retrieval',
        'shortcut':    'Ctrl+4',
        'modules':     ['Search & Query', 'Smart Form Filler', 'Export'],
    },
}

st.markdown('# 🚀 Select Your Workspace')
st.markdown('---')

cols = st.columns(2)
for idx, (name, details) in enumerate(workspaces.items()):
    with cols[idx % 2]:
        st.markdown(
            f'<div class=\'workspace-card\'>'
            f'<div class=\'workspace-title\'>{name}</div>'
            f'<div class=\'workspace-desc\'>{details["description"]}</div>'
            f'<div style=\'margin-top:0.8rem;\'>'
            f'<span class=\'shortcut-hint\'>{details["shortcut"]}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(f'Open {name}', key=f'ws_{idx}', use_container_width=True):
            st.session_state['current_workspace'] = name
            st.switch_page(str(details['page']))

if st.session_state.get('ai_assistant_open'):
    with st.sidebar:
        st.markdown('---')
        st.markdown('### 🤖 AI Assistant')

        user_query = st.text_input('Ask me anything about your documents:')

        if user_query:
            with st.spinner('🧠 Thinking...'):
                st.info(f'You asked: {user_query}')
                st.success('AI Assistant integration point - connect to your LLM/RAG here')

        st.markdown(
            '<div style=\'font-size:0.7rem;color:#546e7a;margin-top:1rem;\'>'
            '💡 Tip: I can explain conflicts, suggest actions, and answer questions about your data.'
            '</div>',
            unsafe_allow_html=True,
        )

with st.expander('⌨️ Keyboard Shortcuts', expanded=False):
    st.markdown('''
    - `Ctrl+1` → Command Hub
    - `Ctrl+2` → Inbox & Actions
    - `Ctrl+3` → Knowledge Brain
    - `Ctrl+4` → Library & Tools
    - `Ctrl+R` → Refresh Data
    - `Ctrl+K` → Toggle AI Assistant
    - `Ctrl+/` → Show Shortcuts
    ''')

st.markdown('---')
st.markdown(
    '<div style=\'text-align:center;color:#546e7a;font-size:0.75rem;\'>'
    '🧠 NASMI 2.0 - Where Intelligence Meets Security'
    '</div>',
    unsafe_allow_html=True,
)