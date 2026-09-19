"""Reusable Streamlit presentation components."""

import streamlit as st

from domain.health import HealthCheck, HealthStatus

_ICONS = {
    HealthStatus.READY: "✅",
    HealthStatus.PENDING: "⏳",
    HealthStatus.ERROR: "❌",
}


def render_health_checks(checks: list[HealthCheck]) -> None:
    columns = st.columns(len(checks))
    for column, check in zip(columns, checks, strict=True):
        with column:
            st.metric(check.component, f"{_ICONS[check.status]} {check.status.value.title()}")
            st.caption(check.message)
