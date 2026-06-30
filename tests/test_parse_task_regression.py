"""Regression guard: parse_task_with_ai is unchanged across the Notes PRD.

Anchors the invariant that `parse_task_with_ai(text, system_prompt)` returns
whatever the configured `AIProvider.parse_task` returns. With the stub provider
patched in, it must surface the canned list verbatim.
"""

from ai_parser import parse_task_with_ai


def test_parse_task_with_ai_returns_canned_response(stub_ai_provider):
    result = parse_task_with_ai("buy milk", "stub-system-prompt")
    assert result == stub_ai_provider.PARSED_TASKS_CANNED
