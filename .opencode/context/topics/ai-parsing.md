# AI Task Parsing + Note Cleanify

> `src/ai_parser.py` + `src/prompt.md` (task parsing) + `src/prompts/notes_cleanify.md` (note tidying). Generic provider abstraction around OpenAI-compatible and Anthropic APIs.

## Provider abstraction
- `AIProvider` base: `__init__(api_key, base_url, model)` + `parse_task(text, system_prompt) -> List[Dict]`.
- `OpenAIProvider` — works for **any OpenAI-compatible endpoint** (OpenAI, Mistral, Infomaniak). Configured via `AI_API_BASE_URL` (default `https://api.openai.com/v1/`) and `AI_MODEL` (default `gpt-3.5-turbo`). Uses raw `requests.post` (not the `openai` SDK) against `{base_url}/chat/completions`.
- `AnthropicProvider` — native Anthropic API when `AI_API_BASE_URL` points at `api.anthropic.com`.
- `get_ai_provider(api_key, base_url, model)` — factory selecting impl by URL heuristics.

## Entry point
`parse_task_with_ai(text, ...)` (called from `app.py` `/api/tasks/parse`):
1. Build provider via `get_ai_provider` using `Config.AI_API_KEY/BASE_URL/MODEL`.
2. Send `text` + `Config.SYSTEM_PROMPT` (loaded once from `src/prompt.md` at startup).
3. `_process_response(response_text)` — strips ` ```json ` / ` ``` ` fences, `json.loads`; accepts **either a single dict or a list of dicts** (multi-task parsing is supported). Each task dict's relative `deadline` ("tomorrow", "next week", "next monday", …) is normalized to an absolute datetime via `datetime.now()`.
4. Returns `List[Dict]` — caller persists each as a `Task`.

## Config / env
- `AI_API_KEY` (preferred) — falls back to legacy `ANTHROPIC_API_KEY` if unset (see `doc/README.md`).
- `AI_API_BASE_URL` — e.g. `https://api.mistral.ai/v1/`, `https://api.anthropic.com/`.
- `AI_MODEL` — e.g. `mistral-small`, `claude-haiku-4-5`, `gpt-3.5-turbo`.
- `SYSTEM_PROMPT` — read from `src/prompt.md` once in `config.py:load_system_prompt()`; missing file falls back to a minimal default string.

## Caveats
- `prompt.md` is the **formatting contract** for the LLM's JSON output — editing it can break `_process_response`'s parsing assumptions. Treat prompt + parser as a pair.
- `openai` SDK is in `requirements.txt` but the OpenAI-compatible provider path uses raw `requests`; the SDK is pulled in for type/compat only.
- Deadline normalization handles a fixed set of English relative phrases — new languages or phrasings need added branches in `_process_response`.

## Note Cleanify seam (separate from task parsing)
- `AIProvider.cleanify(self, note_text: str, system_prompt: str) -> str` — a SIBLING method to `parse_task` on the base class + both concrete providers (`OpenAIProvider`, `AnthropicProvider`). It mirrors `parse_task`'s HTTP setup (headers, endpoint, model selection) but returns the **raw model text** — no `_process_response` JSON extraction. Structural duplication between `cleanify` and `parse_task` within each provider is accepted and preferred over a base-class `complete()` generalization (PRD `001` decision F — explicitly rejected for blast-radius reasons; do NOT introduce `complete()`).
- Top-level factory `cleanify_note_with_ai(note_text, system_prompt) -> str` in `src/ai_parser.py` calls `get_ai_provider().cleanify(...)` and **gracefully degrades**: on any exception OR empty/None response it returns the input `note_text` unchanged (no exception escapes the caller). This is the one-true entry point the Cleanify route (`POST /api/notes/<id>/cleanify`) uses.
- `parse_task` (base + both providers) and `parse_task_with_ai` are **unchanged** in signature and behaviour — the `tests/test_parse_task_regression.py` test (issue 000) anchors this invariant.
- `Config.NOTES_CLEANIFY_PROMPT` — loaded once at startup from `src/prompts/notes_cleanify.md` (`config.py:load_notes_cleanify_prompt()`, sibling to the existing `load_system_prompt()`). Missing file falls back to a default non-empty string. The Cleanify route appends the note's Space context — `"\n\nNote's Space context:\nName: <space.name>\nDescription: <space.description or ''>"` (read via `note.space_rel`) — mirroring how `/api/tasks/parse` appends the available-spaces list.
- The `notes_cleanify.md` prompt is a minimalistic tidying contract (tidy punctuation / line+paragraph breaks / list formatting; preserve the user's wording and intent verbatim where clear; leave unclear sections unchanged rather than guessing; never invent facts / summarize away specifics / convert bullets to prose / rename entities). It is a SYSTEM prompt and does NOT mention spaces.
- Promote-to-task (`POST /api/notes/<id>/promote-to-task`) does NOT add a new AI code path — it reuses `parse_task_with_ai(selected_text, system_prompt)` with the system prompt built the SAME way `/api/tasks/parse` builds it (`Config.SYSTEM_PROMPT` + available-spaces suffix). Drafts returned with `space_id is None` default to the note's `space_id`; the route persists nothing (the client opens `#addTaskModal` / a JS task-confirm modal, then `POST /api/tasks` does the actual create + logs `entity_type='task', action='create'`).
