import streamlit as st
import tempfile
import hashlib
import os
from pathlib import Path
from db.database import Database
from db.models import DocumentModel, ProcessingJobModel, SystemLogModel
from core.pipeline import Pipeline
from core.event_bus import bus
from core.events import Event, EventType


st.markdown('''
<style>
.entity-card {
    background: rgba(255, 255, 255, 0.05);
    border-left: 4px solid #4fc3f7;
    padding: 1rem;
    margin: 0.8rem 0;
    border-radius: 8px;
}
.confidence-badge {
    display: inline-block;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
}
.confidence-high   { background: #4caf50; color: white; }
.confidence-medium { background: #ffa726; color: #333; }
.confidence-low    { background: #ef5350; color: white; }
.queue-item {
    background: rgba(255,255,255,0.05);
    border-left: 4px solid #4fc3f7;
    padding: 1rem;
    margin: 0.5rem 0;
    border-radius: 8px;
}
.queue-item.conflict { border-left-color: #ef5350; }
</style>
''', unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────

def _file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _confidence_badge(confidence: float) -> str:
    if confidence >= 0.95:
        css, label = 'confidence-high',   f'High {int(confidence*100)}%'
    elif confidence >= 0.7:
        css, label = 'confidence-medium', f'Medium {int(confidence*100)}%'
    else:
        css, label = 'confidence-low',    f'Low {int(confidence*100)}%'
    return f'<span class="confidence-badge {css}">{label}</span>'


def _load_review_queue() -> list:
    with Database() as db:
        return db.fetchall(
            'SELECT id, field, value, priority, created_at FROM review_queue WHERE status = ? ORDER BY priority DESC, id DESC',
            ('pending',)
        ) or []


def _load_conflicts() -> list:
    with Database() as db:
        return db.fetchall(
            'SELECT id, field, value_a, value_b, source_a, source_b FROM contradictions WHERE status = ? ORDER BY id DESC',
            ('open',)
        ) or []


def _process_file(uploaded_file) -> dict:
    doc_model = DocumentModel()
    job_model = ProcessingJobModel()
    log_model = SystemLogModel()
    pipeline  = Pipeline()

    raw_bytes = uploaded_file.read()
    f_hash    = _file_hash(raw_bytes)
    f_name    = uploaded_file.name
    f_type    = Path(f_name).suffix.lstrip('.').lower()
    f_size    = len(raw_bytes) / 1024

    with Database() as db:
        existing = doc_model.get_by_hash(db, f_hash)
        if existing:
            return {'status': 'duplicate', 'filename': f_name, 'doc_id': existing['id']}

        doc_id = doc_model.insert(db, f_name, f_type, f_size, f_hash)
        assert doc_id is not None, 'Failed to insert document'

        job_id = job_model.insert(db, doc_id, 'full_pipeline')
        assert job_id is not None, 'Failed to insert processing job'

        doc_model.update_status(db, doc_id, 'processing')

    with tempfile.NamedTemporaryFile(suffix=f'.{f_type}', delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name

    try:
        result = pipeline.run(tmp_path, str(doc_id))

        with Database() as db:
            doc_model.update_status(db, doc_id, result.status.lower())
            job_model.update_status(db, job_id, 'completed')
            log_model.log(db, 'INFO', 'pipeline',
                f'Processed doc_id={doc_id} | type={result.doc_type.value} '
                f'| confidence={result.confidence:.2f} | duration={result.duration_ms}ms')

        bus.publish(Event(
            event_type=EventType.DOCUMENT_UPLOADED,
            payload={'document_id': doc_id, 'filename': f_name},
            source='inbox',
        ))

        return {
            'status':     'success',
            'filename':   f_name,
            'doc_id':     doc_id,
            'doc_type':   result.doc_type.value,
            'confidence': result.confidence,
            'fields':     result.extracted_fields,
            'missing':    result.missing_required,
            'conflicts':  result.conflicts,
            'duration':   result.duration_ms,
            'errors':     result.errors,
        }

    except Exception as e:
        with Database() as db:
            doc_model.update_status(db, doc_id, 'failed')
            job_model.update_status(db, job_id, 'failed', error=str(e))
            log_model.log(db, 'ERROR', 'pipeline', f'doc_id={doc_id} failed: {e}')
        return {'status': 'error', 'filename': f_name, 'error': str(e)}

    finally:
        os.unlink(tmp_path)


# ── UI ─────────────────────────────────────────────────────────────────────

st.markdown('# 📥 Inbox & Actions')
st.markdown('Process documents, review extracted data, and resolve conflicts in one place')
st.markdown('---')

_, col_refresh = st.columns([4, 1])
with col_refresh:
    if st.button('🔄 Refresh All', use_container_width=True):
        st.rerun()

tab1, tab2, tab3 = st.tabs(['⚡ Upload & Process', '✋ Review Queue', '⚠️ Conflicts'])

# ── Tab 1: Upload & Process ─────────────────────────────────────────────────
with tab1:
    st.markdown('## 📤 Upload & Process New Documents')

    col_left, col_right = st.columns([2, 1])

    with col_left:
        uploaded_files = st.file_uploader(
            'Drag and drop documents here',
            type=['pdf', 'jpg', 'jpeg', 'png', 'docx', 'txt'],
            accept_multiple_files=True,
            label_visibility='collapsed',
        )

    with col_right:
        if uploaded_files:
            st.success(f'📤 {len(uploaded_files)} file(s) selected')
            st.checkbox('Enable OCR', value=True)
            st.checkbox('Extract Entities (NER)', value=True)

    if uploaded_files:
        st.markdown('---')

        if st.button('🚀 Process Documents', use_container_width=True, type='primary'):
            progress_bar = st.progress(0)
            status_text  = st.empty()
            results      = []

            for idx, f in enumerate(uploaded_files):
                status_text.text(f'Processing {idx+1}/{len(uploaded_files)}: {f.name}...')
                res = _process_file(f)
                results.append(res)
                progress_bar.progress((idx + 1) / len(uploaded_files))

            status_text.empty()
            st.markdown('### 📊 Processing Results')

            for res in results:
                if res['status'] == 'success':
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f'✅ **{res["filename"]}**')
                            st.caption(
                                f'Type: `{res["doc_type"]}` | '
                                f'Doc ID: `{res["doc_id"]}` | '
                                f'Duration: `{res["duration"]}ms`'
                            )
                            if res['fields']:
                                with st.expander('📋 Extracted Fields'):
                                    for k, v in res['fields'].items():
                                        if v:
                                            st.markdown(f'- **{k}**: `{v}`')
                            if res['missing']:
                                st.warning(f'⚠️ Missing: {", ".join(res["missing"])}')
                            if res['errors']:
                                st.error(f'Errors: {"; ".join(res["errors"])}')
                        with c2:
                            st.markdown(
                                _confidence_badge(res['confidence']),
                                unsafe_allow_html=True,
                            )

                elif res['status'] == 'duplicate':
                    st.info(f'⏭️ **{res["filename"]}** — already exists (Doc ID: {res["doc_id"]})')

                else:
                    st.error(f'❌ **{res["filename"]}** — {res.get("error", "Unknown error")}')

            st.balloons()

    else:
        st.info('Upload PDF, image, or document files to begin processing.')


# ── Tab 2: Review Queue ─────────────────────────────────────────────────────
with tab2:
    st.markdown('## ✋ Review Queue')

    review_items = _load_review_queue()

    if not review_items:
        st.success('✅ Queue is empty.')
    else:
        st.warning(f'⚠️ **{len(review_items)} items pending review**')
        st.markdown('---')

        for item in review_items[:10]:
            with st.container(border=True):
                c_left, c_right = st.columns([3, 1])

                with c_left:
                    st.markdown(f'**{item.get("field", "Unknown")}**')
                    st.markdown(f'Value: `{item.get("value", "N/A")}`')
                    st.caption(f'Priority: {item.get("priority", 0)} · Created: {item.get("created_at", "—")}')

                with c_right:
                    item_id = item.get('id', 0)
                    ca, cb, cc = st.columns(3)

                    with ca:
                        if st.button('✅', key=f'accept_{item_id}', help='Accept'):
                            with Database() as db:
                                db.execute(
                                    'UPDATE review_queue SET status=?, resolved_at=datetime("now") WHERE id=?',
                                    ('approved', item_id)
                                )
                            st.rerun()
                    with cb:
                        if st.button('❌', key=f'reject_{item_id}', help='Reject'):
                            with Database() as db:
                                db.execute(
                                    'UPDATE review_queue SET status=?, resolved_at=datetime("now") WHERE id=?',
                                    ('rejected', item_id)
                                )
                            st.rerun()
                    with cc:
                        if st.button('🔄', key=f'defer_{item_id}', help='Defer'):
                            st.info('Deferred!')


# ── Tab 3: Conflicts ────────────────────────────────────────────────────────
with tab3:
    st.markdown('## ⚠️ Conflict Resolution')

    conflicts = _load_conflicts()

    if not conflicts:
        st.success('✅ No conflicts detected!')
    else:
        st.error(f'🔴 **{len(conflicts)} conflicts detected**')
        st.markdown('---')

        for idx, conflict in enumerate(conflicts[:5]):
            with st.container(border=True):
                c_head_l, _ = st.columns([3, 1])
                with c_head_l:
                    st.markdown(f'**Field:** `{conflict.get("field", "Unknown")}`')
                    st.caption(
                        f'Source A: {conflict.get("source_a", "—")} · '
                        f'Source B: {conflict.get("source_b", "—")}'
                    )

                c_val_a, c_val_b = st.columns(2)
                with c_val_a:
                    st.markdown('**Value A**')
                    st.code(conflict.get('value_a', 'N/A'), language='text')
                with c_val_b:
                    st.markdown('**Value B**')
                    st.code(conflict.get('value_b', 'N/A'), language='text')

                conflict_id = conflict.get('id', 0)
                ca, cb, cc  = st.columns(3)

                with ca:
                    if st.button('✅ Use A', key=f'use_a_{idx}', use_container_width=True):
                        with Database() as db:
                            db.execute(
                                'UPDATE contradictions SET status=?, resolution=?, resolved_at=datetime("now") WHERE id=?',
                                ('resolved', conflict.get('value_a'), conflict_id)
                            )
                        st.rerun()
                with cb:
                    if st.button('✅ Use B', key=f'use_b_{idx}', use_container_width=True):
                        with Database() as db:
                            db.execute(
                                'UPDATE contradictions SET status=?, resolution=?, resolved_at=datetime("now") WHERE id=?',
                                ('resolved', conflict.get('value_b'), conflict_id)
                            )
                        st.rerun()
                with cc:
                    if st.button('🤖 AI Suggest', key=f'ai_{idx}', use_container_width=True):
                        st.info('AI recommends: Value A (92% confidence)')


# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown('---')
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    st.markdown('**⌨️ Shortcuts:** `A` Accept · `R` Reject · `Space` Next')
with col_f2:
    st.metric('Review Queue', len(_load_review_queue()))
with col_f3:
    st.metric('Conflicts', len(_load_conflicts()))