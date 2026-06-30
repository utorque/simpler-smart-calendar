"""Issue 005 — POST /api/notes/<id>/promote-to-task route tests (RED)."""

from conftest import login
from models import Task, Note


def test_promote_returns_task_draft_without_persisting(client, stub_ai_provider, sample_note):
    login(client)
    resp = client.post(f'/api/notes/{sample_note.id}/promote-to-task',
                       json={'selected_text': 'buy milk'})
    assert resp.status_code == 200
    drafts = resp.get_json()
    assert isinstance(drafts, list)
    assert len(drafts) == 1
    assert drafts[0]['title'] == 'buy milk'

    # No Task row was created by the promote call itself.
    assert Task.query.count() == 0

    # The note's content_markdown is unchanged.
    note = Note.query.get(sample_note.id)
    assert note.content_markdown == sample_note.content_markdown


def test_promote_defaults_space_to_note_space_when_llm_returns_none(client, stub_ai_provider, sample_note):
    login(client)
    # stub_ai_provider.parse_task returns space_id=None
    resp = client.post(f'/api/notes/{sample_note.id}/promote-to-task',
                       json={'selected_text': 'buy milk'})
    assert resp.status_code == 200
    drafts = resp.get_json()
    assert drafts[0]['space_id'] == sample_note.space_id  # defaulted from the note


def test_promote_returns_404_for_missing_note(client, stub_ai_provider):
    login(client)
    resp = client.post('/api/notes/9999/promote-to-task',
                        json={'selected_text': 'buy milk'})
    assert resp.status_code == 404
