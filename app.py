from collections.abc import Callable
from pathlib import Path

import streamlit as st

from infrastructure.db.connection import init_db
from ui.layout.page_container import render_page_container
from ui.layout.topbar import render_topbar
from ui.pages.advisory import render as render_advisory
from ui.pages.audit import render as render_audit
from ui.pages.documents import render as render_documents
from ui.pages.forms import render as render_forms
from ui.pages.home import render as render_home
from ui.pages.outputs import render as render_outputs
from ui.pages.profile import render as render_profile
from ui.pages.review import render as render_review
from ui.pages.settings import render as render_settings
from ui.state.page_id import PageId
from ui.state.session_keys import SessionKeys
from ui.state.session_manager import get, init_session

_PAGES: dict[PageId, Callable[[], None]] = {
    PageId.HOME: render_home,
    PageId.DOCUMENTS: render_documents,
    PageId.REVIEW: render_review,
    PageId.PROFILE: render_profile,
    PageId.FORMS: render_forms,
    PageId.ADVISORY: render_advisory,
    PageId.OUTPUTS: render_outputs,
    PageId.AUDIT: render_audit,
    PageId.SETTINGS: render_settings,
}

st.set_page_config(
    page_title="NASMI",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db(Path("data/nasmi.db"))
init_session()
render_topbar()

current_page = PageId(get(SessionKeys.CURRENT_PAGE))
render_page_container(_PAGES.get(current_page, render_home))
