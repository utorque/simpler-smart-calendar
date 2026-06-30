# Data Model

> SQLAlchemy models in `src/models.py`. SQLite file at `instance/tasks.db` (gitignored, Docker-mounted under `/app/instance`). This is the authoritative shape; `doc/PROJECT_DESCRIPTION.md` mirrors it but code is the source of truth.

## Tables

### `tasks`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | auto-increment |
| title | String(500) NOT NULL | |
| description | Text | nullable |
| space | String(100) | **DEPRECATED** — legacy category name, kept for backward compat; use `space_id` |
| space_id | INTEGER FK → spaces.id | current relation |
| priority | INTEGER default 0 | 0-10, higher = more urgent |
| deadline | DateTime | nullable, ISO |
| estimated_duration | INTEGER | minutes (scheduler falls back to 60) |
| scheduled_start / scheduled_end | DateTime | set by `schedule_tasks` |
| completed | Boolean default False | |
| frozen | Boolean default False | pins slot; excluded from reschedule but still blocks others |
| created_at / updated_at | DateTime | utcnow / onupdate utcnow |

`to_dict()` returns a `space` (name) field resolved from `space_rel` if present, falling back to the legacy `space` string — so the UI/API always sees a space name even though the canonical link is `space_id`.

### `spaces`
`id`, `name` (unique), `description` (Text, helps AI infer context), `time_constraints` (Text — JSON string), `created_at`. Helpers `get_time_constraints()` / `set_time_constraints()` round-trip the JSON. Default spaces seeded: `work` (Mon-Fri 09-17), `study` (no constraints), `association` (Wed 18-22).

**time_constraints JSON shape:**
```json
[{"day": 0, "start": "09:00", "end": "17:00"}]  // 0=Mon ... 6=Sun
```

### `change_logs`
Audit trail: `action` (create/update/delete/reorder/freeze/reschedule), `entity_type` (**task/space/note**), `entity_id`, `old_value` / `new_value` (JSON strings), `timestamp`. Intended for future ML preference learning; written opportunistically from app.py handlers.

### `calendar_sources`
`id`, `name`, `ics_url`, `enabled`, `created_at`, `last_fetched`. No scheduling of fetches — `/api/external-events` calls `fetch_external_events` live per request.

### `notes`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | auto-increment |
| space_id | INTEGER FK → spaces.id | **NOT NULL** — every note belongs to a Space; no "unfiled" pseudo-space |
| title | String(500) | nullable — empty title is a valid stored state; the list UI falls back to "Untitled" |
| content_markdown | Text default '' | raw markdown source (the editor is a markdown source editor, not WYSIWYG) |
| created_at / updated_at | DateTime | utcnow / onupdate utcnow |

`Note` model (`src/models.py`) declares `space_rel = db.relationship('Space', backref='notes', foreign_keys=[space_id])` — the canonical Space link; promote-to-task reads `note.space_rel` when injecting Space context into the Cleanify prompt. `to_dict()` returns `{id, space_id, title, content_markdown, created_at, updated_at}` (title returned as-is, including `None`).

Notes mutations log to `change_logs` with `entity_type='note'`, `action` in `{create, update, delete}`, JSON-serialized `Note.to_dict()` snapshots in `old_value`/`new_value` — a Cleanify Apply is just an ordinary `update`. Promote-to-task does NOT log here; it flows through the existing `POST /api/tasks` path and logs as `entity_type='task', action='create'`.

**Intentional absence:** there is NO `source_note_id` column on `tasks`. The link between a promoted task and its source note is conceptual only (PRD `001` Out-of-Scope 4) — a future "jump from task to note" affordance can be added later as a nullable FK if it turns out to matter.

## Schema management caveat
There is **no migration framework** (no Alembic / Flask-Migrate). Tables are created via `db.create_all()` at app startup; schema changes require manual `migrate.py`-style scripts against the prod SQLite file (an explicit open TODO in `doc/TODO.md`). When touching `models.py`, assume existing prod dbs need a hand-written migration.
