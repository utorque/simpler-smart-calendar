# Smart Task Calendar - Project Description

## Project Overview

**Smart Task Calendar** is an ADHD-friendly task management web application that combines AI-powered task parsing with intelligent auto-scheduling. Users can paste natural language text (emails, notes, etc.), and the system automatically extracts task details and schedules them on a calendar based on priority, deadlines, and contextual constraints.

**Current Version**: Production-ready with task freezing feature
**Primary Use**: Self-hosted personal task management
**Target Users**: Individuals with ADHD who need simple, fast task organization

## Technology Stack

### Backend
- **Framework**: Flask 3.0.0+ (Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **AI/ML**: Anthropic Claude 3.5 Haiku (via Anthropic Python SDK 0.75.0+)
- **Authentication**: Flask-Login 0.6.3+ with session-based auth
- **Calendar Integration**: icalendar 5.0.11+ for ICS parsing
- **HTTP Client**: requests 2.31.0+ for external calendar fetching

### Frontend
- **UI Framework**: Bootstrap 5
- **Calendar Component**: FullCalendar.js
- **Drag & Drop**: SortableJS
- **JavaScript**: Vanilla JS (no heavy frameworks)
- **Styling**: Custom CSS with Bootstrap theme

### Infrastructure
- **Containerization**: Docker with Docker Compose
- **Runtime**: Python 3.11+
- **Web Server**: Flask built-in (development) or production WSGI server
- **Database File**: SQLite (`tasks.db` in `/app/instance/`)

## Project Structure

```
simpler-smart-calendar/
├── app.py                      # Main Flask application (480 lines)
├── models.py                   # SQLAlchemy database models (111 lines)
├── ai_parser.py                # AI task parsing logic (88 lines)
├── scheduler.py                # Auto-scheduling algorithm (226 lines)
├── calendar_integration.py     # External calendar ICS fetching (61 lines)
├── config.py                   # Configuration and environment setup (23 lines)
├── prompt.md                   # AI system prompt for task parsing
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker build configuration
├── docker-compose.yml          # Docker Compose orchestration
├── .env.example                # Environment variables template
├── README.md                   # User documentation
├── TODO.md                     # Development roadmap
├── templates/
│   ├── index.html             # Main application UI (10KB)
│   └── login.html             # Login page (2.7KB)
└── static/
    ├── css/
    │   └── style.css          # Custom styles
    └── js/
        └── app.js             # Frontend JavaScript logic
```

## Database Schema

### Tables

#### `tasks`
Primary task storage with scheduling and metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing task ID |
| title | STRING(500) | NOT NULL | Task title |
| description | TEXT | NULLABLE | Detailed task description |
| space | STRING(100) | NULLABLE | Context/category (work, study, etc.) |
| priority | INTEGER | DEFAULT 0 | Priority 0-10, higher = more urgent |
| deadline | DATETIME | NULLABLE | Task deadline (ISO format) |
| estimated_duration | INTEGER | NULLABLE | Duration in minutes |
| scheduled_start | DATETIME | NULLABLE | Scheduled start time |
| scheduled_end | DATETIME | NULLABLE | Scheduled end time |
| completed | BOOLEAN | DEFAULT FALSE | Completion status |
| frozen | BOOLEAN | DEFAULT FALSE | Prevents auto-rescheduling |
| created_at | DATETIME | DEFAULT NOW | Creation timestamp |
| updated_at | DATETIME | ON UPDATE NOW | Last update timestamp |

#### `spaces`
Define contexts with time constraints for scheduling.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing space ID |
| name | STRING(100) | UNIQUE, NOT NULL | Space name (unique) |
| description | TEXT | NULLABLE | Space purpose/context description |
| time_constraints | TEXT | NULLABLE | JSON string of time windows |
| created_at | DATETIME | DEFAULT NOW | Creation timestamp |

**Time Constraints Format**:
```json
[
  {"day": 0, "start": "09:00", "end": "17:00"},  // Monday 9-5
  {"day": 2, "start": "18:00", "end": "22:00"}   // Wednesday 6-10pm
]
```
Days: 0=Monday, 1=Tuesday, ..., 6=Sunday

#### `change_logs`
Audit trail for all user modifications (for future ML learning).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing log ID |
| action | STRING(100) | NOT NULL | Action type (create/update/delete/reorder/freeze) |
| entity_type | STRING(50) | NOT NULL | Entity affected (task/space) |
| entity_id | INTEGER | NULLABLE | ID of affected entity |
| old_value | TEXT | NULLABLE | JSON of previous state |
| new_value | TEXT | NULLABLE | JSON of new state |
| timestamp | DATETIME | DEFAULT NOW | When change occurred |

#### `calendar_sources`
External calendar integrations via ICS URLs.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing source ID |
| name | STRING(100) | NOT NULL | Display name for calendar |
| ics_url | STRING(500) | NOT NULL | ICS feed URL |
| enabled | BOOLEAN | DEFAULT TRUE | Whether to fetch events |
| created_at | DATETIME | DEFAULT NOW | When source was added |
| last_fetched | DATETIME | NULLABLE | Last successful fetch time |

## API Endpoints

### Authentication

#### `POST /login`
Authenticate user with password.

**Request Body**:
```json
{
  "password": "string"
}
```

**Response**:
- `200`: `{"success": true}` - Sets session cookie
- `401`: `{"error": "Invalid password"}`

#### `POST /logout`
Clear authentication session.

**Response**: `{"success": true}`

### Tasks

#### `GET /api/tasks`
Get all tasks (incomplete by default).

**Query Parameters**:
- `include_completed` (boolean): Include completed tasks

**Response**:
```json
[
  {
    "id": 1,
    "title": "Task title",
    "description": "Details",
    "space": "work",
    "priority": 8,
    "deadline": "2025-12-20T23:59:00",
    "estimated_duration": 120,
    "scheduled_start": "2025-12-18T14:00:00",
    "scheduled_end": "2025-12-18T16:00:00",
    "completed": false,
    "frozen": false,
    "created_at": "2025-12-15T10:00:00",
    "updated_at": "2025-12-15T10:00:00"
  }
]
```

#### `POST /api/tasks`
Create a new task manually.

**Request Body**:
```json
{
  "title": "string",
  "description": "string (optional)",
  "space": "string (optional)",
  "priority": "number 0-10 (optional, default 0)",
  "deadline": "ISO datetime string (optional)",
  "estimated_duration": "number in minutes (optional, default 60)"
}
```

**Response**: Task object (201 Created)

#### `POST /api/tasks/parse`
Parse natural language text and create task with AI.

**Request Body**:
```json
{
  "text": "Finish presentation for tomorrow's meeting, 2 hours"
}
```

**Response**: Task object (201 Created)

**AI Processing**:
- Uses Claude 3.5 Haiku model
- System prompt loaded from `prompt.md`
- Extracts: title, description, space, priority, deadline, duration
- Available spaces appended to prompt for context

#### `PUT /api/tasks/<id>`
Update an existing task.

**Request Body**: Partial task object (only fields to update)

**Response**: Updated task object

#### `DELETE /api/tasks/<id>`
Delete a task.

**Response**: `{"success": true}`

#### `POST /api/tasks/<id>/toggle-freeze`
Toggle freeze status for a task.

**Response**:
```json
{
  "success": true,
  "frozen": true
}
```

#### `POST /api/tasks/freeze-day`
Freeze/unfreeze all tasks on a specific day.

**Request Body**:
```json
{
  "date": "2025-12-18"  // YYYY-MM-DD format
}
```

**Response**:
```json
{
  "success": true,
  "count": 5,
  "frozen": true
}
```

**Logic**: If all tasks on day are frozen, unfreezes them; otherwise freezes all.

#### `POST /api/tasks/reorder`
Change task priority by reordering.

**Request Body**:
```json
{
  "task_ids": [3, 1, 2]  // New order (top to bottom)
}
```

**Response**: `{"success": true}`

**Logic**: Assigns priorities based on reverse index in array.

### Scheduling

#### `POST /api/schedule`
Auto-schedule all incomplete tasks.

**Response**:
```json
{
  "success": true,
  "scheduled_tasks": 12
}
```

**Algorithm** (see scheduler.py:4-88):
1. Separate frozen vs non-frozen tasks
2. Sort non-frozen by: priority (desc), deadline (asc), created_at
3. Fetch external calendar events (30 days ahead)
4. Add frozen tasks to "busy slots" to protect them
5. For each task:
   - Find next available slot respecting:
     - Space time constraints
     - External events
     - Frozen tasks
     - Existing scheduled tasks
   - Schedule in 30-minute increments
6. Update task `scheduled_start` and `scheduled_end`

### Spaces

#### `GET /api/spaces`
Get all spaces.

**Response**: Array of space objects

#### `POST /api/spaces`
Create a new space.

**Request Body**:
```json
{
  "name": "string",
  "description": "string (optional)",
  "time_constraints": [
    {"day": 0, "start": "09:00", "end": "17:00"}
  ]
}
```

**Response**: Space object (201 Created)

#### `PUT /api/spaces/<id>`
Update a space.

**Request Body**: Partial space object

**Response**: Updated space object

#### `DELETE /api/spaces/<id>`
Delete a space.

**Response**: `{"success": true}`

### Calendar Sources

#### `GET /api/calendar-sources`
Get all external calendar sources.

**Response**: Array of calendar source objects

#### `POST /api/calendar-sources`
Add an external calendar.

**Request Body**:
```json
{
  "name": "Google Calendar",
  "ics_url": "https://calendar.google.com/...",
  "enabled": true
}
```

**Response**: Calendar source object (201 Created)

#### `DELETE /api/calendar-sources/<id>`
Remove a calendar source.

**Response**: `{"success": true}`

#### `GET /api/external-events`
Fetch events from all enabled external calendars.

**Response**: Array of event objects
```json
[
  {
    "start": "2025-12-18T10:00:00",
    "end": "2025-12-18T11:00:00",
    "title": "Team Meeting",
    "description": "Weekly sync",
    "source": "external"
  }
]
```

**Fetching Logic** (calendar_integration.py):
- Downloads ICS from each enabled source
- Parses with `icalendar` library
- Returns events within next 30 days
- Converts to timezone-naive datetimes

### Logs

#### `GET /api/logs`
Get change logs for audit/learning.

**Query Parameters**:
- `limit` (number): Max logs to return (default 100)

**Response**: Array of change log objects (newest first)

## Core Features

### 1. AI Task Parsing

**File**: `ai_parser.py:6-87`

**Process**:
1. User submits raw text via `/api/tasks/parse`
2. System appends current date to prompt
3. Fetches all spaces and adds descriptions to system prompt
4. Calls Claude 3.5 Haiku with system prompt from `prompt.md`
5. AI returns JSON with task fields
6. Handles relative dates ("tomorrow", "next week", etc.)
7. Creates task in database
8. Logs creation in change_logs

**Fallback**: If no API key, uses simple parsing (first 100 chars as title).

**Prompt Engineering**:
- System prompt loaded once on startup (config.py:7-13)
- Includes space descriptions for context-aware parsing
- Priority guidelines (0-10 scale)
- Duration estimation rules
- Date/time parsing logic

### 2. Auto-Scheduling Algorithm

**File**: `scheduler.py:4-226`

**Constraints**:
- Space time windows (e.g., work only Mon-Fri 9-5)
- External calendar busy times
- Frozen tasks (immovable)
- Task deadlines (must schedule before deadline)
- 30-minute time increments

**Priority System**:
1. Frozen tasks (never moved)
2. Higher priority number (0-10)
3. Closer deadline
4. Earlier creation time

**Search Strategy**:
- Searches up to 90 days ahead
- Stops at deadline if specified
- Finds first available 30-min slot
- Validates against space constraints
- Checks for conflicts with busy slots

### 3. Task Freezing

**Feature Added**: Latest update (see README.md:174-191)

**Functionality**:
- Ctrl+Click on calendar task: Toggle individual freeze
- Ctrl+Click on day header: Freeze/unfreeze all tasks on that day
- Frozen tasks show ❄️ icon and blue styling
- Auto-schedule skips frozen tasks but treats them as busy slots
- Freeze state logged in change_logs

**UI Indicators**:
- Frozen tasks: Blue background, snowflake icon
- Day with frozen tasks: Visual indicator on header

### 4. External Calendar Integration

**File**: `calendar_integration.py`

**Supported Formats**: ICS (iCalendar)

**Compatible Services**:
- Google Calendar (secret ICS URL)
- Outlook/Office 365
- Apple iCloud Calendar
- Any ICS-compatible calendar

**Fetching**:
- On-demand: When user loads external events
- During scheduling: Auto-fetches from enabled sources
- Updates `last_fetched` timestamp
- 30-day lookahead window

### 5. Space-Based Scheduling

**File**: `models.py:42-66`, `scheduler.py:155-226`

**Default Spaces**:
1. **work**: Mon-Fri 9:00-17:00, "Work-related tasks, meetings, and projects"
2. **study**: No constraints, "Learning activities, courses, homework"
3. **association**: Wed 18:00-22:00, "Community group activities"

**Constraint Logic**:
- Tasks with space can only be scheduled in allowed time windows
- Tasks without space or with unconstrained space can be scheduled anytime
- Multiple time windows per space supported
- Day-of-week and time-of-day constraints

### 6. Change Logging

**Purpose**: Track all user actions for future ML-based preference learning

**Logged Actions**:
- `create`: New task/space
- `update`: Task/space modifications
- `delete`: Task/space removal
- `reorder`: Priority changes
- `freeze`/`unfreeze`: Task freeze status changes

**Data Captured**:
- Timestamp
- Entity type and ID
- Old value (JSON)
- New value (JSON)

## Configuration

### Environment Variables

**File**: `.env` (created from `.env.example`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| ANTHROPIC_API_KEY | Yes | None | Claude API key from console.anthropic.com |
| APP_PASSWORD | Yes | "admin" | Single password for app access |
| SECRET_KEY | Yes | Auto-generated | Flask session secret (use random string) |
| FLASK_ENV | No | "development" | "development" or "production" |

### Application Config

**File**: `config.py`

**Settings**:
- Database: SQLite at `sqlite:///tasks.db`
- Session tracking: Disabled
- System prompt: Loaded from `prompt.md` at startup
- Port: 53000 (app.py:480) or 5000 (Docker)

## Deployment

### Docker (Recommended)

**Build & Run**:
```bash
docker-compose up -d
```

**What Happens**:
1. Builds Python 3.11 slim image
2. Installs requirements
3. Exposes port 5000
4. Mounts `./instance` for persistent database
5. Loads environment from `.env`
6. Runs `python app.py`

**Data Persistence**:
- Database stored in `./instance/tasks.db` (host volume)
- Survives container restarts/rebuilds

### Manual Installation

**Requirements**: Python 3.11+

**Steps**:
1. Create virtualenv: `python -m venv venv`
2. Activate: `source venv/bin/activate`
3. Install deps: `pip install -r requirements.txt`
4. Create `.env` from `.env.example`
5. Run: `python app.py`
6. Access: http://localhost:53000

### Production Considerations

- Change `APP_PASSWORD` from default
- Generate random `SECRET_KEY` (e.g., `python -c "import secrets; print(secrets.token_hex(32))"`)
- Set `FLASK_ENV=production`
- Use production WSGI server (gunicorn, waitress)
- Enable HTTPS
- Regular database backups of `instance/tasks.db`

## Development Notes

### Database Migrations

**No formal migration system** - uses SQLAlchemy `db.create_all()`

**Past Migrations**:
- Locations → Spaces rename (migrate_locations_to_spaces.py - removed)
- Add `frozen` column (migration.py - removed)
- Add `description` to spaces

**Manual Changes**: Modify models.py and handle data migration manually.

### Default Data Initialization

**File**: `app.py:452-476`

On first run, creates 3 default spaces if none exist.

### Testing

**Status**: No test suite currently
**TODO**: Add pytest tests (see TODO.md)

### Code Style

- No formal linting configured
- Uses Flask conventions
- Function docstrings for public functions
- Type hints: Not used

## Key Algorithms

### Task Priority Sorting

**File**: `app.py:59`, `scheduler.py:23-29`

```python
query.order_by(Task.priority.desc(), Task.deadline.asc())
```

**Logic**:
1. Higher priority first
2. If same priority, earlier deadline first
3. If no deadline, treated as datetime.max (last)

### Time Slot Conflict Detection

**File**: `scheduler.py:150-152`

```python
def slots_overlap(start1, end1, start2, end2):
    return start1 < end2 and end1 > start2
```

**Logic**: Two slots overlap if start of one is before end of other AND vice versa.

### Next Valid Time for Space

**File**: `scheduler.py:201-225`

**Process**:
1. If no constraints, return current time
2. Search next 90 days
3. For each day, check if weekday matches constraint
4. Find constraint with start time >= current time
5. Return constraint start time

## Frontend Architecture

### Main Application

**File**: `templates/index.html`

**Components**:
- Task input area (top)
- Task list (left 1/3, draggable with SortableJS)
- FullCalendar (right 2/3)
- Modals: Edit task, manage spaces, add calendar

**Key Features**:
- Drag-to-reorder tasks
- Drag/resize calendar events
- Ctrl+Click for freezing
- Real-time calendar updates

### JavaScript

**File**: `static/js/app.js`

**Key Functions** (assumed based on features):
- `loadTasks()`: Fetch and render task list
- `loadSpaces()`: Fetch spaces for dropdowns
- `parseTask()`: Submit text to AI parser
- `autoSchedule()`: Trigger scheduling algorithm
- `saveTask()`: Create/update task
- `deleteTask()`: Remove task
- `reorderTasks()`: Send new order to API
- `toggleFreeze()`: Freeze/unfreeze task
- `freezeDay()`: Freeze/unfreeze day

**Calendar Integration**:
- FullCalendar configuration
- Event drag/drop/resize handlers
- External event fetching and rendering

### Styling

**File**: `static/css/style.css`

**Features**:
- Bootstrap 5 base theme
- Custom task priority colors
- Frozen task styling (blue, snowflake)
- Responsive layout
- Mobile-friendly interface

## Authentication

**Type**: Session-based, single-user

**Flow**:
1. User visits `/` → redirects to `/login` if not authenticated
2. User submits password
3. Server checks against `APP_PASSWORD` env var
4. If valid, sets `session['authenticated'] = True`
5. All API endpoints protected with `@login_required` decorator

**Security**:
- Session cookie (Flask default)
- No user registration
- Single shared password
- No password hashing (single-user app)

## Future Roadmap

**File**: `TODO.md`

**Planned Features**:
- [ ] Space ID instead of name in tasks (data integrity)
- [ ] "Add context and re-plan" button
- [ ] Web-based auto-update (docker-compose pull/up from UI)
- [ ] Current date/time in scheduler (avoid past scheduling)
- [ ] Task completion UI improvements
- [ ] Context-based task filtering
- [ ] Model selection UI
- [ ] User habit learning from change_logs
- [ ] System prompt optimization
- [ ] UI/UX refresh (softer design)
- [ ] Completed tasks view
- [ ] Space-based task filtering
- [ ] Space-scoped rescheduling

**Long-Term** (from README):
- Audio recording for task creation
- File attachments
- Multi-user support
- Mobile/desktop apps
- Natural language scheduling
- Recurring tasks
- Task templates
- Collaboration features

## Quick Reference

### Common File Locations

| What | Where |
|------|-------|
| Main app entry | `app.py` |
| Database models | `models.py` |
| Scheduling logic | `scheduler.py` |
| AI parsing | `ai_parser.py` |
| System prompt | `prompt.md` |
| Environment config | `.env` (not tracked) |
| Database file | `instance/tasks.db` |
| Frontend UI | `templates/index.html` |
| API routes | `app.py` (lines 25-448) |

### Key Line Ranges

| Feature | File:Lines |
|---------|------------|
| Task endpoints | app.py:50-300 |
| Freeze functionality | app.py:204-272 |
| Auto-schedule | app.py:303-335 |
| Space endpoints | app.py:339-386 |
| Calendar endpoints | app.py:389-439 |
| AI parsing | ai_parser.py:6-87 |
| Scheduling algorithm | scheduler.py:4-88 |
| Slot finding | scheduler.py:91-147 |
| Space constraints | scheduler.py:155-198 |
| Database models | models.py:7-111 |

### Important Behaviors

1. **Frozen Tasks**: Never moved by auto-schedule but block other tasks
2. **Priority Scale**: 0-10, where 10 is critical/ASAP
3. **Time Increments**: All scheduling in 30-minute blocks
4. **Default Duration**: 60 minutes if not specified
5. **Space Matching**: AI uses space descriptions for context detection
6. **Deadline Behavior**: Tasks without deadlines can be scheduled anytime
7. **External Events**: Fetched on-demand and during auto-schedule
8. **Change Logs**: All actions logged for future learning
9. **Session Timeout**: Flask default (31 days if permanent, browser session if not)
10. **Database Init**: Auto-creates tables and default spaces on first run

## Version History

**Current State** (Dec 2025):
- ✅ Task freezing (ctrl+click, day freezing)
- ✅ Space-based scheduling with descriptions
- ✅ External calendar integration (ICS)
- ✅ AI task parsing (Claude 3.5 Haiku)
- ✅ Auto-scheduling algorithm
- ✅ Change logging
- ✅ Docker deployment
- ✅ Drag-and-drop UI
- ✅ Priority-based ordering

**Recent Changes** (from git log):
- Task freezing feature (commit 2ebb0d6)
- Migration scripts cleanup
- README capitalization fix

## Support & Documentation

- **README.md**: User-facing documentation
- **TODO.md**: Development roadmap
- **LICENSE**: Apache 2.0 (assumed based on LICENSE file presence)
- **Issues**: GitHub issues (mention in README)

---

**Last Updated**: 2025-12-15
**Documentation Version**: 1.0
**Project Status**: Production-ready, actively maintained
