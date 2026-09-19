"""Document upload and indexing page."""

import streamlit as st

from ui.runtime import get_runtime
from ui.workspace import render_document_panel

st.title("Documents")
render_document_panel(get_runtime())
