"""Streamlit entrypoint for the enterprise knowledge assistant."""

import streamlit as st

from app.logging import configure_logging
from ui.components import render_health_checks
from ui.runtime import get_runtime
from ui.workspace import render_chat_panel, render_document_panel

st.set_page_config(
    page_title="Enterprise Knowledge Assistant",
    page_icon="📚",
    layout="wide",
)

runtime = get_runtime()
configure_logging(runtime.settings.log_level)

st.title("Enterprise Knowledge Assistant")
st.write(
    "Ask grounded questions over your organization's documents and inspect the evidence "
    "behind every answer."
)

with st.expander("Service readiness"):
    render_health_checks(runtime.health_service().run())

left, right = st.columns([0.9, 1.1], gap="large")
with left:
    render_document_panel(runtime)
with right:
    render_chat_panel(runtime)
