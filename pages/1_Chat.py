"""Grounded document chat page."""

import streamlit as st

from ui.runtime import get_runtime
from ui.workspace import render_chat_panel

st.title("Chat")
render_chat_panel(get_runtime())
