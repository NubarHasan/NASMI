import streamlit as st
from db.database import Database


st.markdown('''
<style>
.entity-node {
    background: linear-gradient(135deg, #ba68c8 0%, #9c27b0 100%);
    padding: 1rem;
    border-radius: 8px;
    color: white;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(186, 104, 200, 0.3);
}
.entity-node:hover { transform: scale(1.05); box-shadow: 0 8px 24px rgba(186, 104, 200, 0.5); }
.address-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
    border: 1px solid #4fc3f7;
    border-radius: 8px;
    padding: 1.2rem;
    margin: 0.8rem 0;
}
.address-header { font-weight: 700; color: #4fc3f7; font-size: 1.1rem; margin-bottom: 0.5rem; }
.address-detail { color: #b0bec5; font-size: 0.9rem; margin: 0.3rem 0; }
.timeline-item { display: flex; margin: 1rem 0; }
.timeline-dot {
    width: 12px; height: 12px;
    background: #4fc3f7; border-radius: 50%;
    margin-right: 1rem; margin-top: 0.25rem; flex-shrink: 0;
    box-shadow: 0 0 12px rgba(79, 195, 247, 0.5);
}
.timeline-content {
    flex: 1; background: rgba(255,255,255,0.05);
    padding: 1rem; border-radius: 6px; border-left: 2px solid #4fc3f7;
}
.timeline-date { font-size: 0.8rem; color: #90caf9; font-weight: 600; }
.timeline-title { color: #e0e0e0; font-weight: 600; margin: 0.3rem 0; }
.timeline-desc { font-size: 0.85rem; color: #b0bec5; }
.identity-card {
    background: linear-gradient(135deg, #1a4d2e 0%, #2d5a3d 100%);
    border: 2px solid #4caf50; border-radius: 12px; padding: 2rem; color: white;
}
.identity-field { display: grid; grid-template-columns: 1fr 2fr; margin: 0.8rem 0; gap: 1rem; }
.identity-label { font-weight: 600; color: #a5d6a7; }
.identity-value { color: #e0e0e0; }
.trust-score { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.7rem; font-weight: 700; margin-left: 0.5rem; }
.trust-score.high { background: #4caf50; color: white; }
.trust-score.medium { background: #ffa726; color: #333; }
.trust-score.low { background: #ef5350; color: white; }
.field-book-entry {
    background: rgba(255,255,255,0.05);
    border: 1px solid #ba68c8; border-radius: 8px; padding: 1rem; margin: 0.5rem 0;
}
</style>
''', unsafe_allow_html=True)

if 'brain_state' not in st.session_state:
    st.session_state['brain_state'] = {
        'selected_entity': None,
        'graph_zoom': 1.0,
    }


def get_trust_badge(confidence: float) -> str:
    if confidence >= 0.95:
        css, label = 'high', f'{int(confidence * 100)}%'
    elif confidence >= 0.7:
        css, label = 'medium', f'{int(confidence * 100)}%'
    else:
        css, label = 'low', f'{int(confidence * 100)}%'
    return f'<span class="trust-score {css}">{label}</span>'


def load_entities() -> list:
    with Database() as db:
        rows = db.fetchall(
            'SELECT DISTINCT entity_value, entity_type, confidence FROM entities ORDER BY confidence DESC LIMIT 50'
        )
    return rows or []


def load_timeline_events() -> list:
    with Database() as db:
        rows = db.fetchall(
            'SELECT event_type, event_date, description, source FROM timeline_events ORDER BY event_date DESC LIMIT 10'
        )
    return rows or []


def load_addresses() -> list:
    with Database() as db:
        rows = db.fetchall(
            'SELECT label, value, field_type, created_at FROM address_fields ORDER BY created_at DESC LIMIT 20'
        )
    return rows or []


def load_identity() -> dict:
    with Database() as db:
        row = db.fetchone('SELECT * FROM identity_core ORDER BY id DESC LIMIT 1')
    return row or {}


def load_field_book() -> list:
    with Database() as db:
        rows = db.fetchall(
            'SELECT field, value, confidence, source FROM knowledge ORDER BY confidence DESC LIMIT 20'
        )
    return rows or []


st.markdown('# 🧠 Knowledge Brain - Cognitive Layer')
st.markdown('Entity relationships, timeline, addresses, and identity core')
st.markdown('---')

_, col_right = st.columns([3, 1])
with col_right:
    if st.button('🔄 Refresh Brain', use_container_width=True):
        st.rerun()

tabs = st.tabs(['🕸️ Entity Graph', '👥 Address Book', '📅 Timeline', '🪪 Identity Core', '📇 Field Book'])

# ── Tab 0 : Entity Graph ───────────────────────────────────────────────────
with tabs[0]:
    st.markdown('## Entity Knowledge Graph')
    entities = load_entities()

    if not entities:
        st.info('No entities discovered yet. Upload documents to begin.')
    else:
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.markdown('### Interactive Entity Graph')
            for entity in entities[:10]:
                val  = entity.get('entity_value', 'Unknown')
                typ  = entity.get('entity_type', 'Unknown')
                conf = float(entity.get('confidence', 0))
                st.markdown(
                    f'<div class="entity-node" style="margin:0.5rem 0;">'
                    f'<div style="display:flex;justify-content:space-between;">'
                    f'<span>{val}</span>{get_trust_badge(conf)}</div>'
                    f'<div style="font-size:0.8rem;opacity:0.8;margin-top:0.3rem;">{typ}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        with col_right:
            st.markdown('### Entity Stats')
            avg_conf = sum(float(e.get('confidence', 0)) for e in entities) / len(entities)
            st.metric('Total Entities', len(entities))
            st.metric('Unique Types', len({e.get('entity_type') for e in entities}))
            st.metric('Avg Confidence', f'{int(avg_conf * 100)}%')
            q = st.text_input('🔍 Search entities', placeholder='Type to search...')
            if q:
                st.write(f'Found {sum(1 for e in entities if q.lower() in str(e).lower())} results')

# ── Tab 1 : Address Book ───────────────────────────────────────────────────
with tabs[1]:
    st.markdown('## 👥 Address Book')
    addresses = load_addresses()

    if not addresses:
        st.info('No addresses recorded yet.')
    else:
        col_left, col_right = st.columns([2, 1])
        with col_left:
            for addr in addresses[:15]:
                label = addr.get('label', '—')
                value = addr.get('value', '—')
                ftype = addr.get('field_type', '—')
                st.markdown(
                    f'<div class="address-card">'
                    f'<div class="address-header">{label}</div>'
                    f'<div class="address-detail">📋 {ftype}</div>'
                    f'<div class="address-detail">📌 {value}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with col_right:
            st.markdown('### Quick Actions')
            if st.button('➕ Add Address', use_container_width=True):
                st.info('Add address dialog would open here')
            if st.button('📥 Import', use_container_width=True):
                st.info('Import dialog would open here')
            if st.button('📤 Export', use_container_width=True):
                st.success('Export downloaded!')

# ── Tab 2 : Timeline ───────────────────────────────────────────────────────
with tabs[2]:
    st.markdown('## 📅 Timeline - Life Events & History')
    events = load_timeline_events()

    if not events:
        st.info('No timeline events recorded yet.')
    else:
        for ev in events[:8]:
            st.markdown(
                f'<div class="timeline-item">'
                f'<div class="timeline-dot"></div>'
                f'<div class="timeline-content">'
                f'<div class="timeline-date">{ev.get("event_date", "—")}</div>'
                f'<div class="timeline-title">{ev.get("event_type", "Unknown")}</div>'
                f'<div class="timeline-desc">{ev.get("description", "No description")}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

# ── Tab 3 : Identity Core ──────────────────────────────────────────────────
with tabs[3]:
    st.markdown('## 🪪 Identity Core - Primary Identity')
    identity = load_identity()

    if not identity:
        st.warning('No primary identity set yet.')
    else:
        st.markdown(
            f'<div class="identity-card">'
            f'<h3 style="margin-top:0;">{identity.get("full_name", "Unknown")}</h3>'
            f'<div class="identity-field"><div class="identity-label">ID Number</div>'
            f'<div class="identity-value">{identity.get("id_number", "—")}</div></div>'
            f'<div class="identity-field"><div class="identity-label">Date of Birth</div>'
            f'<div class="identity-value">{identity.get("birth_date", "—")}</div></div>'
            f'<div class="identity-field"><div class="identity-label">Nationality</div>'
            f'<div class="identity-value">{identity.get("nationality", "—")}</div></div>'
            f'<div class="identity-field"><div class="identity-label">Status</div>'
            f'<div class="identity-value">{identity.get("status", "active")}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Tab 4 : Field Book ─────────────────────────────────────────────────────
with tabs[4]:
    st.markdown('## 📇 Field Book - Knowledge Registry')
    fields = load_field_book()

    if not fields:
        st.info('No fields registered yet.')
    else:
        for f in fields:
            conf = float(f.get('confidence', 0))
            st.markdown(
                f'<div class="field-book-entry">'
                f'<strong>{f.get("field", "—")}</strong>'
                f'{get_trust_badge(conf)}'
                f'<div style="font-size:0.8rem;color:#90caf9;margin:0.3rem 0;">'
                f'Source: {f.get("source", "—")}</div>'
                f'<div style="color:#b0bec5;">{f.get("value", "—")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.markdown('---')
st.markdown('💡 The Knowledge Brain automatically clusters related entities, detects life events, and maintains relationships across all documents.')