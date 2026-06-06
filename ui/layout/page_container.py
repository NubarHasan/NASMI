from collections.abc import Callable

import streamlit as st

_CSS = """
<style>
.block-container {
    padding-top: 0.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px;
}
header[data-testid="stHeader"] { display: none; }
footer { display: none; }
#MainMenu { display: none; }
</style>
"""


def render_page_container(renderer: Callable[[], None]) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    with st.container():
        renderer()
