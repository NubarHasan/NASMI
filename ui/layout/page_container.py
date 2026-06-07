from collections.abc import Callable

import streamlit as st

_CSS = """
<style>
.block-container {
    padding-top: 0.8rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1500px;
}
header[data-testid="stHeader"] {
    display: none;
}
footer {
    display: none;
}
#MainMenu {
    display: none;
}
.stButton button {
    border-radius: 10px;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #1e293b;
    background: #020617;
}
</style>
"""


def render_page_container(renderer: Callable[[], None]) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    with st.container():
        renderer()
