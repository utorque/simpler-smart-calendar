# Notes Module

> In-app ADHD-friendly note capture with promote-to-task and Cleanify. PRD `001` (archived: `.opencode/plans/archive/001_PRD_notes.md`). Notes are a first-class destination alongside the calendar — thoughts get captured into the currently-selected Space, tidied with one click, and promoted into a task with a single selection+click, all without crossing application boundaries.

## Information architecture
- `/notes` — server-rendered route (`src/templates/notes.html`, login via `session['authenticated']` like `/`); NOT `@login_required`-decorated (it mirrors `/`'s session-check-and-redirect, since `login_required` returns JSON 401 not an HTML redirect). All `/api/notes/*` JSON routes ARE `@login_required`.
- Reuses the existing `GET /api/spaces` for its Space switcher; filter state (selected Space) persisted to `localStorage`. A top-level "Notes" nav button lives in `index.html` (and `login.html`).
- Auth: no new auth model — reuses the single shared `APP_PASSWORD` + session cookie.

## Editor: EasyMDE (CodeMirror 5)
- Loaded via CDN (`<script src="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.js">` + CSS), matching the project's no-build CDN pattern (FullCalendar / SortableJS / Bootstrap). Frontend logic in `src/static/js/notes.js`.
- **Mandatory config:** `autosave: {enabled: false}` (EasyMDE's built-in localStorage autosave would shadow the backend `PUT` path), explicit minimal custom toolbar (NOT the default formatting toolbar — a bold/italic/heading toolbar would collide with Cleanify's job, which is to tidy formatting FOR the user), `status: false`.
- Toolbar = three custom buttons only: `add-task` (promote selection to task), `cleanify` (tidy whole note via LLM), `undo-cleanify` (single-step restore). The same actions are also surfaced as standalone HTML buttons (`#addTaskBtn`, `#cleanifyBtn`, `#undoCleanifyBtn`) below the editor.
- Selection handling (promote-to-task contract): `editor.codemirror.getSelection()` reads the selection; `editor.codemirror.somethingSelected()` toggles the `add-task` button's disabled state on `cursorActivity`/`change` (robust across browsers, wrapped lines, and iPad soft-keyboards).
- Content replacement (Cleanify Apply): `editor.value(cleanedText)` overwrites the buffer; the CM5 `change` event fires the existing debounced `PUT`-on-input autosave, so the cleaned text persists through the normal path (no special Apply step).

## Deferred persistence (client-side lifecycle)
- "+" opens an empty editor bound to the currently-selected Space with **no row created yet**.
- A debounced (~800ms) autosave fires on every content change. First time it would fire with non-empty `content_markdown` (or non-empty `title`) → `POST /api/notes`; subsequent saves → `PUT /api/notes/<id>`.
- Navigating away / unmounting while `content_markdown == ""` AND `title == ""` AND no prior POST = nothing persisted. No empty "Untitled" cadavers.

## Routes (`src/app.py`, all `login_required`, JSON in/out)
- `GET /api/notes?space_id=<id>` → note DTOs for that Space, ordered by `updated_at` desc (full DTOs incl. content; client previews content for the list).
- `POST /api/notes` → `{space_id, title?, content_markdown?}` creates + logs `entity_type='note', action='create'`. `space_id` NOT NULL enforced.
- `GET /api/notes/<id>` → single DTO (404 if missing).
- `PUT /api/notes/<id>` → any subset of `{title, content_markdown, space_id}` → updated DTO + `action='update'`. Used for ordinary debounced autosave AND Cleanify Apply.
- `DELETE /api/notes/<id>` → 204 + `action='delete'`.
- `POST /api/notes/<id>/cleanify` → body `{}` → `{content: <string>}`. Builds `Config.NOTES_CLEANIFY_PROMPT` + the note's Space context suffix, calls `cleanify_note_with_ai(note.content_markdown, system_prompt)`. **Does not persist** (the client replaces editor content + the existing debounced `PUT` autosave persists). On AI failure → `{content: <original note content>}` (graceful degradation via `cleanify_note_with_ai`'s try/except).
- `POST /api/notes/<id>/promote-to-task` → `{selected_text}` → list of task draft DTOs (same shape `/api/tasks/parse` returns). Builds system prompt = `Config.SYSTEM_PROMPT` + available-spaces suffix (same as `/api/tasks/parse`), calls `parse_task_with_ai(selected_text, ...)`, defaults each draft's `space_id` to `note.space_id` when the LLM returns `None`. **Does not persist a Task**; client opens the task-confirm modal, user confirms → existing `POST /api/tasks` creates the task. Note left completely untouched.

## Frontend task-confirm modal
- The calendar page's `#addTaskModal` (in `index.html`) is NOT loaded on `/notes` and only accepts free text + calls `/api/tasks/parse` (which creates). So `/notes` ships a self-contained JS-only confirm modal (`openPromoteTaskModal` in `notes.js`) pre-filled with a draft, whose confirm POSTs to the existing `POST /api/tasks`. For multiple drafts from one selection, the modal opens once per draft in sequence; cancel stops the loop. Single-draft path is the tested/automated case.

## Cleanify Undo (single-step, client-side)
- On Cleanify: `previousContent` (= `state.lastCleaned`) stores the pre-clean buffer, `editor.value(resp.content)` replaces in place, "Undo Cleanify" shown.
- On Undo: `editor.value(previousContent)` restores, "Undo" hidden. `lastCleaned` reset to `null` on note switch / editor clear. NOT an ephemeral toast — persistent until clicked or until next Cleanify overwrites (per PRD decision E: an accidental click must be reversible reliably even after a stray keystroke).

## Testing
- HTTP route-layer integration tests via the Flask test client + one unit-level seam on the AI provider's `cleanify` method (see `.opencode/context/topics/ai-parsing.md`). Harness in `tests/conftest.py`: in-memory SQLite (`StaticPool`), per-test schema reset + default-space seeding (work/study/association), `StubAIProvider` (canned `parse_task` + `cleanify`), `stub_ai_provider_raising`, `sample_note`, `login(client)` helper. Test files: `test_parse_task_regression.py` (000), `test_notes_crud.py` (001), `test_cleanify_ai_seam.py` (002), `test_cleanify_prompt_loaded.py` (003), `test_cleanify_route.py` (004), `test_promote_to_task_route.py` (005).
- Frontend interactions (drag/select/EasyMDE) are NOT covered by automated tests (no browser driver) — manual verification only.

## Invariants (do NOT break)
- No `source_note_id` column on `Task` (PRD Out-of-Scope 4 — conceptual link only).
- `parse_task` code path unchanged in signature/behaviour (regression test 000 anchors this).
- No `AIProvider.complete()` generalization (decision F — `cleanify` is a sibling method).
- Notes Cleanify prompt loaded once at startup and cached; no per-request file reads.
