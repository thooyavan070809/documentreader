"""Smoke tests for the Streamlit application shell."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_home_page_starts_without_provider_credentials() -> None:
    entrypoint = Path(__file__).parents[2] / "streamlit_app.py"
    app = AppTest.from_file(entrypoint, default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "Enterprise Knowledge Assistant"
    assert len(app.get("file_uploader")) == 1
    assert len(app.text_area) == 1
    assert app.text_area[0].label == "Question"


def test_documents_page_starts_without_provider_credentials() -> None:
    entrypoint = Path(__file__).parents[2] / "streamlit_app.py"
    app = AppTest.from_file(entrypoint, default_timeout=30).run()
    app.switch_page("pages/2_Documents.py").run()

    assert not app.exception
    assert app.title[0].value == "Documents"
    assert len(app.get("file_uploader")) == 1
