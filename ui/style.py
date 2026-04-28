import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>

        /* ── Base ── */
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #0a0f1e;
            color: #e8eaf6;
            font-family: 'Segoe UI', sans-serif;
        }

        [data-testid="stSidebar"] {
            background-color: #0d1526;
            border-right: 1px solid #1e2d4a;
        }

        /* ── Sidebar Title ── */
        .sidebar-logo {
            text-align: center;
            padding: 1.5rem 0 1rem 0;
        }
        .sidebar-logo h1 {
            font-size: 1.8rem;
            font-weight: 800;
            color: #4fc3f7;
            letter-spacing: 3px;
            margin: 0;
        }
        .sidebar-logo p {
            font-size: 0.65rem;
            color: #546e7a;
            letter-spacing: 2px;
            margin: 0;
            text-transform: uppercase;
        }

        /* ── Nav Items ── */
        [data-testid="stSidebarNav"] a {
            color: #90a4ae !important;
            font-size: 0.9rem;
            padding: 0.4rem 1rem;
            border-radius: 6px;
            transition: all 0.2s;
        }
        [data-testid="stSidebarNav"] a:hover {
            background-color: #1a2744;
            color: #4fc3f7 !important;
        }
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background-color: #1565c0 !important;
            color: #ffffff !important;
            font-weight: 600;
        }

        /* ── Page Header ── */
        .page-header {
            padding: 1rem 0 0.5rem 0;
            border-bottom: 2px solid #1565c0;
            margin-bottom: 1.5rem;
        }
        .page-header h2 {
            font-size: 1.6rem;
            font-weight: 700;
            color: #e3f2fd;
            margin: 0;
        }
        .page-header p {
            font-size: 0.8rem;
            color: #546e7a;
            margin: 0.2rem 0 0 0;
        }

        /* ── Metric Cards ── */
        [data-testid="stMetric"] {
            background-color: #0d1a2e;
            border: 1px solid #1e2d4a;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            transition: border-color 0.2s;
        }
        [data-testid="stMetric"]:hover {
            border-color: #1565c0;
        }
        [data-testid="stMetricLabel"] {
            color: #546e7a !important;
            font-size: 0.75rem !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        [data-testid="stMetricValue"] {
            color: #4fc3f7 !important;
            font-size: 1.8rem !important;
            font-weight: 700 !important;
        }

        /* ── Buttons ── */
        [data-testid="stButton"] > button {
            background-color: #1565c0;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1.2rem;
            font-weight: 600;
            transition: background-color 0.2s;
        }
        [data-testid="stButton"] > button:hover {
            background-color: #1976d2;
        }
        [data-testid="stButton"] > button:disabled {
            background-color: #1a2744;
            color: #37474f;
        }

        /* ── Inputs ── */
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] > div {
            background-color: #0d1a2e !important;
            border: 1px solid #1e2d4a !important;
            color: #e8eaf6 !important;
            border-radius: 8px !important;
        }
        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
            border-color: #1565c0 !important;
            box-shadow: 0 0 0 2px rgba(21,101,192,0.3) !important;
        }

        /* ── Tabs ── */
        [data-testid="stTabs"] [role="tab"] {
            color: #546e7a;
            font-weight: 500;
            border-radius: 6px 6px 0 0;
        }
        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            color: #4fc3f7;
            border-bottom: 2px solid #1565c0;
        }

        /* ── Info / Warning / Error boxes ── */
        [data-testid="stAlert"] {
            border-radius: 8px;
            border-left: 4px solid #1565c0;
            background-color: #0d1a2e;
        }

        /* ── Divider ── */
        hr {
            border-color: #1e2d4a;
        }

        /* ── Status Badges ── */
        .badge {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        .badge-active   { background: #1b5e20; color: #a5d6a7; }
        .badge-expired  { background: #b71c1c; color: #ef9a9a; }
        .badge-pending  { background: #e65100; color: #ffcc80; }
        .badge-conflict { background: #4a148c; color: #ce93d8; }
        .badge-new      { background: #0d47a1; color: #90caf9; }

        /* ── Cards ── */
        .nasmi-card {
            background-color: #0d1a2e;
            border: 1px solid #1e2d4a;
            border-radius: 12px;
            padding: 1.2rem;
            margin-bottom: 0.8rem;
            transition: border-color 0.2s, transform 0.1s;
        }
        .nasmi-card:hover {
            border-color: #1565c0;
            transform: translateY(-1px);
        }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0a0f1e; }
        ::-webkit-scrollbar-thumb { background: #1e2d4a; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #1565c0; }

        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(icon: str, title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class='page-header'>
            <h2>{icon} {title}</h2>
            {'<p>' + subtitle + '</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, status: str = "new") -> str:
    return f"<span class='badge badge-{status}'>{text}</span>"
