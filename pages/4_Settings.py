"""Safe runtime configuration and connectivity diagnostics."""

import streamlit as st

from ui.components import render_health_checks
from ui.runtime import get_runtime

st.title("Settings and health")
runtime = get_runtime()

run_live_qdrant_check = st.button(
    "Check Qdrant Cloud connection",
    disabled=not runtime.settings.qdrant_configured,
)
render_health_checks(
    runtime.health_service().run(check_qdrant_live=run_live_qdrant_check)
)

st.subheader("Safe configuration summary")
st.json(runtime.settings.safe_summary())
st.caption("Secret values are never displayed on this page.")
