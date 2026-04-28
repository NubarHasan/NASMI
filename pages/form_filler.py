import streamlit as st
from ui.style import apply_theme, page_header, badge

apply_theme()
page_header('📝', 'Smart Form Filler', 'Fields are extracted and filled automatically from your Knowledge Base')

# ── Session State ─────────────────────────────────────
if 'fill_mode' not in st.session_state:
    st.session_state.fill_mode = 'Suggest Only'
if 'uploaded_form' not in st.session_state:
    st.session_state.uploaded_form = None

# ── Layout ───────────────────────────────────────────
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown('#### ⚙️ Fill Configuration')

    # ── Fill Mode ──
    fill_mode = st.radio(
        'Fill Mode',
        ['Suggest Only', 'Assisted Fill', 'Identity Locked Fill'],
        horizontal=False,
        help=(
            'Suggest Only: shows suggestions without filling\n'
            'Assisted Fill: fills fields + allows override\n'
            'Identity Locked Fill: uses Identity Core only — no override'
        ),
    )

    mode_info = {
        'Suggest Only':           ('new',     'Shows best match per field — you decide'),
        'Assisted Fill':          ('pending', 'Auto-fills fields — you can override any value'),
        'Identity Locked Fill':   ('active',  'Uses Identity Core only — locked, no override'),
    }
    m_status, m_desc = mode_info[fill_mode]
    st.markdown(
        f"<div class='nasmi-card' style='padding:0.6rem 1rem;'>"
        f"{badge(fill_mode, m_status)}"
        f"<div style='font-size:0.78rem;color:#546e7a;margin-top:0.4rem;'>{m_desc}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Upload Form ──
    st.markdown('#### 📂 Upload Form to Fill')
    uploaded_form = st.file_uploader(
        'Upload a form',
        type=['pdf', 'docx', 'png', 'jpg'],
        label_visibility='collapsed',
        help='Upload the form you want NASMI to fill',
    )

    if uploaded_form:
        st.session_state.uploaded_form = uploaded_form
        ext = uploaded_form.name.split('.')[-1].upper()
        st.markdown(
            f"<div class='nasmi-card' style='display:flex;justify-content:space-between;"
            f"align-items:center;padding:0.6rem 1rem;'>"
            f"<span style='color:#e3f2fd;font-size:0.85rem;'>{uploaded_form.name}</span>"
            f"{badge(ext, 'new')}"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Fill Source ──
    st.markdown('#### 🗂️ Fill Source')
    fill_source = st.selectbox(
        'Source',
        ['Knowledge Base (Auto)', 'Specific Document', 'Manual Input'],
        label_visibility='collapsed',
    )

    if fill_source == 'Specific Document':
        st.selectbox('Select Document', ['— No documents yet —'])

    st.divider()

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        detect_btn = st.button(
            '🔍 Detect Fields',
            use_container_width=True,
            disabled=not uploaded_form,
        )
    with col_btn2:
        st.button(
            '📤 Export Filled Form',
            use_container_width=True,
            disabled=True,
        )

with col_right:
    st.markdown('#### 📋 Detected Fields')

    if not st.session_state.uploaded_form:
        st.markdown(
            "<div class='nasmi-card' style='text-align:center;padding:3rem 1rem;"
            "color:#37474f;border:2px dashed #1e2d4a;'>"
            "<div style='font-size:2rem;'>📋</div>"
            "<div style='margin-top:0.5rem;font-size:0.9rem;'>No form uploaded yet</div>"
            "<div style='font-size:0.75rem;margin-top:0.3rem;'>"
            "Upload a form — NASMI will detect all fillable fields automatically."
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    else:
        # ── Field Detection Pipeline Status ──
        if detect_btn:
            st.markdown(
                "<div class='nasmi-card' style='padding:0.6rem 1rem;"
                "color:#546e7a;font-size:0.85rem;'>"
                "🔄 Field detection pipeline will be active once the engine is connected."
                "</div>",
                unsafe_allow_html=True,
            )

        # ── Dynamic Fields Preview ──
        st.markdown(
            "<div style='font-size:0.75rem;color:#546e7a;margin-bottom:0.5rem;'>"
            "Fields below are detected automatically from the uploaded form."
            "</div>",
            unsafe_allow_html=True,
        )

        # ── Mock Fields (replace with dynamic extraction later) ──
        mock_fields = [
            ('Full Name',       None,  'PERSON',   'active',   95),
            ('Date of Birth',   None,  'DATE',     'active',   91),
            ('Nationality',     None,  'GPE',      'active',   88),
            ('Address',         None,  'ADDRESS',  'pending',  74),
            ('Document Number', None,  'ID',       'new',      0),
            ('IBAN',            None,  'FINANCE',  'new',      0),
        ]

        for field, value, entity_type, status, confidence in mock_fields:
            filled    = value is not None
            disp_val  = value if filled else ''
            conf_text = f'{confidence}% confidence' if confidence > 0 else 'Not found in Knowledge Base'
            conf_color= '#a5d6a7' if confidence >= 80 else '#ffcc80' if confidence >= 50 else '#ef9a9a'

            st.markdown(
                f"<div class='nasmi-card' style='padding:0.8rem 1rem;margin-bottom:0.5rem;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<span style='font-size:0.8rem;color:#546e7a;text-transform:uppercase;"
                f"letter-spacing:0.5px;'>{field}</span>"
                f"<div style='display:flex;gap:0.4rem;align-items:center;'>"
                f"{badge(entity_type, status)}"
                f"<span style='font-size:0.7rem;color:{conf_color};'>{conf_text}</span>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            if fill_mode == 'Identity Locked Fill':
                st.text_input(
                    field,
                    value=disp_val,
                    disabled=True,
                    label_visibility='collapsed',
                    key=f'locked_{field}',
                )
            elif fill_mode == 'Assisted Fill':
                st.text_input(
                    field,
                    value=disp_val,
                    placeholder='Auto-fill from Knowledge Base...',
                    label_visibility='collapsed',
                    key=f'assisted_{field}',
                )
            else:
                col_f, col_s = st.columns([3, 1])
                with col_f:
                    st.text_input(
                        field,
                        value='',
                        placeholder=f'Suggested: {disp_val or "—"}',
                        label_visibility='collapsed',
                        key=f'suggest_{field}',
                    )
                with col_s:
                    st.button(
                        '✅ Use',
                        key=f'use_{field}',
                        use_container_width=True,
                        disabled=not filled,
                    )

            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        # ── Fill Summary ──
        filled_count = sum(1 for _, v, *_ in mock_fields if v is not None)
        total_count  = len(mock_fields)
        pct          = int((filled_count / total_count) * 100) if total_count else 0

        st.markdown(
            f"<div class='nasmi-card' style='display:flex;justify-content:space-between;"
            f"align-items:center;padding:0.8rem 1.2rem;'>"
            f"<span style='color:#546e7a;font-size:0.85rem;'>Fields Filled</span>"
            f"<span style='color:#4fc3f7;font-weight:700;'>{filled_count} / {total_count} ({pct}%)</span>"
            f"</div>",
            unsafe_allow_html=True,
        )