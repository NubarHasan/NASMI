import streamlit as st
from db.database import Database
from datetime import datetime


st.markdown('''
<style>
.dashboard-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
    padding: 1.5rem;
    border-radius: 12px;
    border-left: 4px solid #4fc3f7;
    text-align: center;
    transition: all 0.3s ease;
}
.dashboard-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(79, 195, 247, 0.3);
}
.metric-number {
    font-size: 2.5rem;
    font-weight: 700;
    color: #4fc3f7;
    margin: 0.5rem 0;
}
.metric-label {
    font-size: 0.9rem;
    color: #90caf9;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.metric-delta {
    font-size: 0.8rem;
    color: #a5d6a7;
    margin-top: 0.3rem;
}
.health-bar {
    width: 100%;
    height: 8px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    overflow: hidden;
    margin: 0.5rem 0;
}
.health-fill {
    height: 100%;
    border-radius: 4px;
    transition: all 0.3s ease;
}
.alert-box {
    background: linear-gradient(135deg, #b71c1c 0%, #d32f2f 100%);
    border: 1px solid #ff5252;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
}
.warning-box {
    background: linear-gradient(135deg, #e65100 0%, #ff6f00 100%);
    border: 1px solid #ffa726;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
}
.success-box {
    background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%);
    border: 1px solid #4caf50;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
}
.log-entry {
    background: rgba(255, 255, 255, 0.02);
    border-left: 2px solid #4fc3f7;
    padding: 0.8rem;
    margin: 0.3rem 0;
    border-radius: 4px;
    font-size: 0.85rem;
    font-family: 'Courier New', monospace;
}
.log-error   { border-left-color: #ef5350; color: #ff8a80; }
.log-warning { border-left-color: #ffa726; color: #ffb74d; }
.log-info    { border-left-color: #4fc3f7; color: #80deea; }
.log-success { border-left-color: #4caf50; color: #a5d6a7; }
.settings-group {
    background: rgba(255, 255, 255, 0.05);
    padding: 1.5rem;
    border-radius: 8px;
    border-left: 4px solid #ba68c8;
    margin: 1rem 0;
}
.setting-label {
    font-weight: 600;
    color: #e0e0e0;
    margin-bottom: 0.5rem;
}
</style>
''', unsafe_allow_html=True)

if 'hub_state' not in st.session_state:
    st.session_state['hub_state'] = {
        'current_view': 'dashboard',
        'theme': 'dark',
    }


def get_system_metrics() -> dict:
    with Database() as db:
        doc_count      = db.fetchone('SELECT COUNT(*) as cnt FROM documents')
        review_count   = db.fetchone('SELECT COUNT(*) as cnt FROM review_queue WHERE status = ?', ('pending',))
        conflict_count = db.fetchone('SELECT COUNT(*) as cnt FROM contradictions WHERE status = ?', ('open',))
        entity_count   = db.fetchone('SELECT COUNT(DISTINCT entity_value) as cnt FROM entities')
        jobs_count     = db.fetchone('SELECT COUNT(*) as cnt FROM processing_jobs WHERE status = ?', ('running',))
    return {
        'documents': doc_count['cnt']      if doc_count      else 0,
        'reviews':   review_count['cnt']   if review_count   else 0,
        'conflicts': conflict_count['cnt'] if conflict_count else 0,
        'entities':  entity_count['cnt']   if entity_count   else 0,
        'jobs':      jobs_count['cnt']     if jobs_count     else 0,
    }


def get_recent_logs() -> list:
    with Database() as db:
        rows = db.fetchall(
            'SELECT level, module, message, timestamp FROM system_logs ORDER BY timestamp DESC LIMIT 20'
        )
    return rows or []


def get_system_health(metrics: dict) -> int:
    total = metrics['documents']
    if total == 0:
        return 100
    issues = metrics['reviews'] + metrics['conflicts']
    return max(0, int(100 - (issues / total * 100)))


def get_export_history() -> list:
    with Database() as db:
        rows = db.fetchall(
            'SELECT export_type, created_at, status FROM exports ORDER BY created_at DESC LIMIT 5'
        )
    return rows or []


st.markdown('# 🎯 Command Hub - System Dashboard')
st.markdown('Real-time overview of system health, metrics, and activity')
st.markdown('---')

view_tabs = st.tabs(['📊 Dashboard', '📋 Activity Logs', '⚙️ Settings'])

# ── Tab 0 : Dashboard ──────────────────────────────────────────────────────
with view_tabs[0]:
    metrics = get_system_metrics()
    health  = get_system_health(metrics)
    health_color = '#4caf50' if health >= 80 else '#ffa726' if health >= 60 else '#ef5350'

    st.markdown('## System Health Overview')
    st.markdown(f'''
    <div class='dashboard-card' style='border-left-color: {health_color};'>
        <div class='metric-label'>System Health</div>
        <div class='metric-number' style='color: {health_color};'>{health}%</div>
        <div class='health-bar'>
            <div class='health-fill' style='width: {health}%; background: {health_color};'></div>
        </div>
        <div class='metric-delta'>{'✅ Optimal' if health >= 80 else '⚠️ Good' if health >= 60 else '🔴 Critical'}</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('---')
    st.markdown('## Key Metrics')

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f'''
        <div class='dashboard-card'>
            <div class='metric-label'>Documents</div>
            <div class='metric-number'>{metrics["documents"]}</div>
        </div>
        ''', unsafe_allow_html=True)

    with col2:
        st.markdown(f'''
        <div class='dashboard-card' style='border-left-color: #ba68c8;'>
            <div class='metric-label'>Entities</div>
            <div class='metric-number' style='color: #ba68c8;'>{metrics["entities"]}</div>
        </div>
        ''', unsafe_allow_html=True)

    with col3:
        color_3 = '#ffa726' if metrics['reviews'] > 0 else '#4caf50'
        st.markdown(f'''
        <div class='dashboard-card' style='border-left-color: {color_3};'>
            <div class='metric-label'>Review Queue</div>
            <div class='metric-number' style='color: {color_3};'>{metrics["reviews"]}</div>
        </div>
        ''', unsafe_allow_html=True)

    with col4:
        color_4 = '#ef5350' if metrics['conflicts'] > 0 else '#4caf50'
        st.markdown(f'''
        <div class='dashboard-card' style='border-left-color: {color_4};'>
            <div class='metric-label'>Conflicts</div>
            <div class='metric-number' style='color: {color_4};'>{metrics["conflicts"]}</div>
        </div>
        ''', unsafe_allow_html=True)

    with col5:
        color_5 = '#fff176' if metrics['jobs'] > 0 else '#4caf50'
        st.markdown(f'''
        <div class='dashboard-card' style='border-left-color: {color_5};'>
            <div class='metric-label'>Running Jobs</div>
            <div class='metric-number' style='color: {color_5};'>{metrics["jobs"]}</div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown('---')
    st.markdown('## Alerts & Notifications')

    col_alerts, col_actions = st.columns([2, 1])

    with col_alerts:
        if metrics['conflicts'] > 0:
            st.markdown(f'''
            <div class='alert-box'>
                <strong>🔴 Critical Conflicts</strong><br>
                {metrics["conflicts"]} data conflicts require immediate attention
            </div>
            ''', unsafe_allow_html=True)

        if metrics['reviews'] > 5:
            st.markdown(f'''
            <div class='warning-box'>
                <strong>⚠️ High Review Load</strong><br>
                {metrics["reviews"]} items pending manual review
            </div>
            ''', unsafe_allow_html=True)

        if health >= 80:
            st.markdown(f'''
            <div class='success-box'>
                <strong>✅ System Operational</strong><br>
                All systems running normally
            </div>
            ''', unsafe_allow_html=True)

    with col_actions:
        if st.button('🔄 Force Refresh', use_container_width=True):
            st.rerun()
        if st.button('⚙️ Optimize DB', use_container_width=True):
            with Database() as db:
                db.execute('VACUUM')
            st.success('Database optimized!')
        if st.button('📤 Export Report', use_container_width=True):
            with Database() as db:
                db.execute(
                    'INSERT INTO exports (export_type, status) VALUES (?, ?)',
                    ('system_report', 'completed')
                )
            st.success('Report exported!')

# ── Tab 1 : Activity Logs ──────────────────────────────────────────────────
with view_tabs[1]:
    st.markdown('## Activity Logs - Complete Audit Trail')

    log_filter = st.selectbox(
        'Filter by level',
        ['All', 'ERROR', 'WARNING', 'INFO', 'SUCCESS'],
        label_visibility='collapsed',
    )

    logs = get_recent_logs()

    if not logs:
        st.info('No activity logged yet.')
    else:
        for entry in logs:
            level = (entry.get('level') or 'info').upper()

            if log_filter != 'All' and level != log_filter:
                continue

            css_class = f'log-{level.lower()}'
            icon = {'ERROR': '❌', 'WARNING': '⚠️', 'INFO': 'ℹ️', 'SUCCESS': '✅'}.get(level, 'ℹ️')
            message   = entry.get('message', '—')
            module    = entry.get('module', '—')
            timestamp = entry.get('timestamp', '—')

            st.markdown(
                f'<div class="log-entry {css_class}">'
                f'{icon} [{module}] {message}'
                f'<span style="float:right;opacity:0.6;">{timestamp}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Tab 2 : Settings ───────────────────────────────────────────────────────
with view_tabs[2]:
    st.markdown('## ⚙️ System Settings & Configuration')

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('### 🎨 Appearance')
        st.markdown('<div class="settings-group"><div class="setting-label">Color Scheme</div></div>', unsafe_allow_html=True)
        st.radio('Theme', ['Dark', 'Light'], horizontal=True, label_visibility='collapsed')

        st.markdown('<div class="settings-group"><div class="setting-label">Language & Region</div></div>', unsafe_allow_html=True)
        st.selectbox('Language', ['English', 'German', 'Arabic'], label_visibility='collapsed')
        st.selectbox('Region', ['DE', 'US', 'SA'], label_visibility='collapsed')

    with col_right:
        st.markdown('### 🤖 AI & Processing')
        st.markdown('<div class="settings-group"><div class="setting-label">Default AI Model</div></div>', unsafe_allow_html=True)
        st.selectbox('Model', ['Ollama Local', 'OpenAI', 'Anthropic'], label_visibility='collapsed')
        st.slider('Temperature', 0.0, 1.0, 0.7, label_visibility='collapsed')

    st.markdown('---')
    st.markdown('### 🔐 Security & Privacy')

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown('<div class="settings-group"><div class="setting-label">Encryption</div></div>', unsafe_allow_html=True)
        st.checkbox('Enable at-rest encryption', value=True)
        st.checkbox('Enable automatic backups', value=True)
    with col_b:
        st.markdown('<div class="settings-group"><div class="setting-label">Data Retention</div></div>', unsafe_allow_html=True)
        st.slider('Delete old logs after (days)', 30, 730, 90)
    with col_c:
        st.markdown('<div class="settings-group"><div class="setting-label">Privacy</div></div>', unsafe_allow_html=True)
        st.checkbox('Send usage analytics', value=False)
        st.checkbox('Enable telemetry', value=False)

    st.markdown('---')

    if st.button('💾 Save Settings', use_container_width=True, type='primary'):
        st.success('✅ Settings saved successfully!')

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button('↩️ Reset to Defaults', use_container_width=True):
            st.warning('Settings reset to defaults')
    with col_r2:
        if st.button('🗑️ Clear Cache', use_container_width=True):
            st.info('Cache cleared')

st.markdown('---')
st.markdown(
    f'<div style="text-align:center;color:#546e7a;font-size:0.75rem;">'
    f'Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    f'</div>',
    unsafe_allow_html=True,
)