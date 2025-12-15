# Smart Task Calendar - ADHD-Friendly Task Manager

A simple, fast, and intuitive web application designed specifically for people with ADHD to manage tasks and automatically schedule them on a calendar.

## Features

### Core Functionality
- **AI-Powered Task Creation**: Simply paste text (emails, notes, etc.) and let AI extract task details
- **Smart Scheduling**: Automatically schedules tasks based on priority, deadlines, and availability
- **Visual Task Management**: Drag-and-drop task reordering and calendar scheduling
- **External Calendar Integration**: Import events from Google Calendar, Outlook, and other ICS-compatible calendars
- **Space-Based Scheduling**: Define time constraints for different contexts (work, study, personal projects, etc.)
- **Change Logging**: Track all modifications for future learning and preferences

### User Interface
- **Simple Layout**: 1/3 task list, 2/3 calendar view
- **Priority-Based Ordering**: Tasks automatically sorted by urgency and deadline
- **Drag-and-Drop**: Reorder tasks and reschedule calendar events easily
- **Real-Time Updates**: Calendar reflects changes immediately
- **Mobile Responsive**: Works on desktop, tablet, and mobile devices

## Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed
- Anthropic API key (for AI task parsing)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd simpler-smart-calendar
```

2. Create a `.env` file:
```bash
cp .env.example .env
```

3. Edit `.env` and set your configuration:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
APP_PASSWORD=your_secure_password_here
SECRET_KEY=your_random_secret_key_here
FLASK_ENV=production
```

4. Start the application:
```bash
docker-compose up -d
```

5. Access the application at `http://localhost:5000`

## Manual Installation

### Prerequisites
- Python 3.11 or higher
- pip

### Setup

1. Clone the repository and navigate to it:
```bash
git clone <repository-url>
cd simpler-smart-calendar
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```bash
cp .env.example .env
```

5. Edit `.env` and configure your settings

6. Run the application:
```bash
python app.py
```

7. Access at `http://localhost:5000`

## Usage Guide

### Creating Tasks

1. **Quick Create**: Type or paste your task description in the input area at the top
2. **AI Parsing**: Click "Create Task with AI" to automatically extract:
   - Task title
   - Description
   - Space/context
   - Priority (0-10)
   - Deadline
   - Estimated duration

### Managing Tasks

- **Reorder**: Drag tasks up or down to change priority
- **Edit**: Click on any task to edit details
- **Complete**: Mark tasks as completed in the edit dialog
- **Delete**: Remove tasks from the edit dialog

### Auto-Scheduling

1. Click "Auto-Schedule All" to automatically place tasks on your calendar
2. The algorithm considers:
   - Task priority (higher priority scheduled first)
   - Deadlines (urgent tasks scheduled sooner)
   - Space time constraints
   - Existing calendar events

### Calendar Management

- **Drag Events**: Move scheduled tasks to different times
- **Resize Events**: Adjust duration by dragging event edges
- **External Calendars**: Add Google/Outlook calendars via ICS URLs

### Space Management

1. Click "Manage Spaces" to view/edit contexts
2. Define time constraints for each space:
   - Example: "work" only on weekdays 9-5
   - Example: "association" only Wednesday evenings
3. Add descriptions to spaces to help AI understand context

### Adding External Calendars

1. Click "Add Calendar"
2. Enter calendar name and ICS URL
3. Get ICS URLs from:
   - **Google Calendar**: Settings → Calendar Settings → Secret address in iCalendar format
   - **Outlook**: Calendar → Share → ICS

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key for AI task parsing (get one at https://console.anthropic.com/)
- `APP_PASSWORD`: Single password to access the application
- `SECRET_KEY`: Secret key for Flask sessions (generate a random string)
- `FLASK_ENV`: Set to `production` for production deployment

### Default Spaces

The app comes with three default spaces:
- **work**: Monday-Friday, 9:00-17:00
  - Description: Work-related tasks, meetings, and projects during office hours
- **study**: No time constraints
  - Description: Learning activities, courses, homework, and educational tasks
- **association**: Wednesday, 18:00-22:00
  - Description: Community group, club, or volunteer organization activities

You can modify or add more spaces through the UI.

### Migrating from Previous Versions

If you're upgrading from a version that used "Locations" instead of "Spaces", run the migration script before starting the updated application:

```bash
python migrate_locations_to_spaces.py
```

This will:
- Rename the `locations` table to `spaces`
- Rename the `location` column in tasks to `space`
- Add the `description` column to spaces
- Create a backup of your database before migration

### AI Task Parsing

The AI task parsing is powered by Anthropic's Claude 3.5 Haiku model. The system prompt is stored in `prompt.md` and loaded once on application startup. This makes it easy to customize the AI's behavior without modifying code:

1. Edit `prompt.md` to adjust how tasks are parsed
2. Restart the application to load the updated prompt
3. The prompt includes guidelines for extracting titles, spaces, priorities, deadlines, and durations

## API Endpoints

### Tasks
- `GET /api/tasks` - Get all tasks
- `POST /api/tasks` - Create a new task
- `POST /api/tasks/parse` - Parse text and create task with AI
- `PUT /api/tasks/<id>` - Update a task
- `DELETE /api/tasks/<id>` - Delete a task
- `POST /api/tasks/reorder` - Reorder tasks

### Scheduling
- `POST /api/schedule` - Auto-schedule all tasks

### Spaces
- `GET /api/spaces` - Get all spaces
- `POST /api/spaces` - Create a space
- `PUT /api/spaces/<id>` - Update a space
- `DELETE /api/spaces/<id>` - Delete a space

### Calendar Sources
- `GET /api/calendar-sources` - Get all calendar sources
- `POST /api/calendar-sources` - Add a calendar source
- `DELETE /api/calendar-sources/<id>` - Remove a calendar source
- `GET /api/external-events` - Get events from external calendars

### Logs
- `GET /api/logs` - Get change logs

## Architecture

### Backend
- **Flask**: Web framework
- **SQLite**: Database for tasks, spaces, and logs
- **Anthropic Claude**: AI-powered task parsing (using Claude 3.5 Haiku)
- **icalendar**: ICS calendar parsing

### Frontend
- **Bootstrap 5**: UI framework
- **FullCalendar**: Calendar component
- **SortableJS**: Drag-and-drop functionality
- **Vanilla JavaScript**: No heavy frameworks for fast performance

### Database Schema

- **tasks**: Store task information, priorities, deadlines, schedules, and associated space
- **spaces**: Define contexts (work, study, etc.) with descriptions and time constraints
- **change_logs**: Track all user modifications
- **calendar_sources**: Store external calendar ICS URLs

## Development

### Running Tests
```bash
# Coming soon
pytest
```

### Building Docker Image
```bash
docker build -t smart-task-calendar .
```

### Contributions
Contributions are welcome! Please feel free to submit issues and pull requests.

## Roadmap

### Future Features
- Audio recording support for task creation
- File attachment support
- Preferences learning from change logs
- Multi-user support
- Mobile app (iOS/Android)
- Desktop app (Electron)
- Natural language scheduling ("schedule this for tomorrow morning")
- Recurring tasks
- Task templates
- Collaboration features
- Integration with more calendar services

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.

## Credits

Built with ADHD users in mind - designed to be as simple and fast as possible to reduce friction in task management.
