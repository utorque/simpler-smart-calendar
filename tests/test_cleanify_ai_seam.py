"""
Unit tests for the cleanify AI seam (issue 002).

These are the one allowed unit-test seam on AIProvider.cleanify (see PRD
decision I): the LLM is the seam, so a StubAIProvider returning canned text is
used to assert on `cleanify_note_with_ai`'s post-processing contract
(canned passthrough + graceful degradation) without going through the route
layer.
"""

from ai_parser import parse_task_with_ai, cleanify_note_with_ai


def test_cleanify_note_with_ai_returns_canned_text(stub_ai_provider):
    # stub_ai_provider.cleanify returns "cleaned"
    result = cleanify_note_with_ai("messy text", "stub-system-prompt")
    assert result == "cleaned"


def test_cleanify_note_with_ai_returns_input_on_error(stub_ai_provider_raising):
    # stub_ai_provider_raising.cleanify raises Exception
    result = cleanify_note_with_ai("messy text", "stub-system-prompt")
    assert result == "messy text"  # graceful degradation: input returned unchanged


def test_parse_task_with_ai_still_works(stub_ai_provider):
    # regression — must remain unchanged
    result = parse_task_with_ai("buy milk", "stub-system-prompt")
    assert result == stub_ai_provider.PARSED_TASKS_CANNED
