"""
Issue 003 — Config loads src/prompts/notes_cleanify.md once at startup into
Config.NOTES_CLEANIFY_PROMPT (sibling to the existing SYSTEM_PROMPT load).

We assert against `Config` directly (the load happens at import time of
config.py, before any Flask app exists) AND confirm the value propagates to
`app.config['NOTES_CLEANIFY_PROMPT']` via Flask's `from_object`, which is the
read surface the issue-004 route handler will use. We also assert the source
prompt file exists on disk.

(The issue's literal test takes the `app` fixture; the conftest `app` fixture
is currently broken on pytest 9 — the `@pytest.fixture def app():` decorator
rebinds the module name `app` to the fixture, so `with app.app_context()` inside
the fixture raises AttributeError. This test avoids that fixture and reads the
class attr + the already-imported module-level `app` directly, exactly the
fallback the issue specifies: "fall back to asserting
`from config import Config; Config.NOTES_CLEANIFY_PROMPT` is non-empty ...
prefer the app.config[...] form; make it work.")
"""

import os

from config import Config


def _prompt_path():
    return os.path.join(
        os.path.dirname(__file__), '..', 'src', 'prompts', 'notes_cleanify.md'
    )


def test_notes_cleanify_prompt_loaded_at_startup():
    # Config.NOTES_CLEANIFY_PROMPT is a non-empty string loaded once at startup.
    prompt = Config.NOTES_CLEANIFY_PROMPT
    assert isinstance(prompt, str)
    assert len(prompt) > 0

    # The source file exists on disk.
    assert os.path.exists(_prompt_path())

    # The existing SYSTEM_PROMPT load path is untouched (regression guard).
    assert isinstance(Config.SYSTEM_PROMPT, str)
    assert len(Config.SYSTEM_PROMPT) > 0

    # The value propagates to the Flask app's config via from_object — this is
    # the read surface issue 004's route handler will use
    # (`app.config['NOTES_CLEANIFY_PROMPT']`). Importing `app` here reuses the
    # already-imported module (conftest imports it after redirecting the DB
    # URI to in-memory), so no prod state is touched.
    from app import app as flask_app
    assert flask_app.config['NOTES_CLEANIFY_PROMPT'] == prompt
