from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
from models import db, Task, Space, ChangeLog, CalendarSource
from config import Config
import json
import os
from ai_parser import parse_task_with_ai
from scheduler import schedule_tasks
from calendar_integration import fetch_external_events

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Authentication decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@app.route('/')
def index():
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.json.get('password')
        if password == app.config['APP_PASSWORD']:
            session['authenticated'] = True
            return jsonify({'success': True})
        return jsonify({'error': 'Invalid password'}), 401
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('authenticated', None)
    return jsonify({'success': True})


# Task endpoints
@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    include_completed = request.args.get('include_completed', 'false').lower() == 'true'

    query = Task.query
    if not include_completed:
        query = query.filter_by(completed=False)

    tasks = query.order_by(Task.priority.desc(), Task.deadline.asc()).all()
    return jsonify([task.to_dict() for task in tasks])


@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.json

    task = Task(
        title=data['title'],
        description=data.get('description'),
        space=data.get('space'),
        priority=data.get('priority', 0),
        deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else None,
        estimated_duration=data.get('estimated_duration', 60)
    )

    db.session.add(task)
    db.session.commit()

    # Log the creation
    log = ChangeLog(
        action='create',
        entity_type='task',
        entity_id=task.id,
        new_value=json.dumps(task.to_dict())
    )
    db.session.add(log)
    db.session.commit()

    return jsonify(task.to_dict()), 201


@app.route('/api/tasks/parse', methods=['POST'])
@login_required
def parse_task():
    data = request.json
    text = data.get('text')

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    ### Append list of spaces to the system prompt

    spaces = Space.query.all()
    space_names = [space.name for space in spaces]
    spaces_descs = "\n".join([f"- {space.name}: {space.description}" for space in spaces])

    system_prompt = app.config['SYSTEM_PROMPT'] + "\n\nAvailable spaces:\n" + spaces_descs

    task_data = parse_task_with_ai(text, app.config['ANTHROPIC_API_KEY'], system_prompt)

    task = Task(
        title=task_data['title'],
        description=task_data.get('description'),
        space=task_data.get('space'),
        priority=task_data.get('priority', 0),
        deadline=datetime.fromisoformat(task_data['deadline']) if task_data.get('deadline') else None,
        estimated_duration=task_data.get('estimated_duration', 60)
    )

    db.session.add(task)
    db.session.commit()

    # Log the creation
    log = ChangeLog(
        action='create',
        entity_type='task',
        entity_id=task.id,
        new_value=json.dumps(task.to_dict())
    )
    db.session.add(log)
    db.session.commit()

    return jsonify(task.to_dict()), 201


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    old_value = task.to_dict()

    data = request.json

    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'space' in data:
        task.space = data['space']
    if 'priority' in data:
        task.priority = data['priority']
    if 'deadline' in data:
        task.deadline = datetime.fromisoformat(data['deadline']) if data['deadline'] else None
    if 'estimated_duration' in data:
        task.estimated_duration = data['estimated_duration']
    if 'scheduled_start' in data:
        task.scheduled_start = datetime.fromisoformat(data['scheduled_start']) if data['scheduled_start'] else None
    if 'scheduled_end' in data:
        task.scheduled_end = datetime.fromisoformat(data['scheduled_end']) if data['scheduled_end'] else None
    if 'completed' in data:
        task.completed = data['completed']
    if 'frozen' in data:
        task.frozen = data['frozen']

    db.session.commit()

    # Log the update
    log = ChangeLog(
        action='update',
        entity_type='task',
        entity_id=task.id,
        old_value=json.dumps(old_value),
        new_value=json.dumps(task.to_dict())
    )
    db.session.add(log)
    db.session.commit()

    return jsonify(task.to_dict())


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    old_value = task.to_dict()

    db.session.delete(task)
    db.session.commit()

    # Log the deletion
    log = ChangeLog(
        action='delete',
        entity_type='task',
        entity_id=task_id,
        old_value=json.dumps(old_value)
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True})


@app.route('/api/tasks/<int:task_id>/toggle-freeze', methods=['POST'])
@login_required
def toggle_task_freeze(task_id):
    task = Task.query.get_or_404(task_id)
    old_value = task.to_dict()

    task.frozen = not task.frozen
    db.session.commit()

    # Log the freeze/unfreeze
    log = ChangeLog(
        action='freeze' if task.frozen else 'unfreeze',
        entity_type='task',
        entity_id=task.id,
        old_value=json.dumps(old_value),
        new_value=json.dumps(task.to_dict())
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'frozen': task.frozen})


@app.route('/api/tasks/freeze-day', methods=['POST'])
@login_required
def freeze_day():
    data = request.json
    date_str = data.get('date')

    if not date_str:
        return jsonify({'error': 'No date provided'}), 400

    # Parse the date (format: YYYY-MM-DD)
    target_date = datetime.fromisoformat(date_str).date()

    # Find all tasks scheduled on this day
    tasks_on_day = Task.query.filter(
        db.func.date(Task.scheduled_start) == target_date
    ).all()

    if not tasks_on_day:
        return jsonify({'success': True, 'count': 0, 'message': 'No tasks found on this day'})

    # Toggle freeze status for all tasks on this day
    # If all are frozen, unfreeze them; otherwise freeze all
    all_frozen = all(task.frozen for task in tasks_on_day)
    new_frozen_state = not all_frozen

    for task in tasks_on_day:
        old_value = task.to_dict()
        task.frozen = new_frozen_state

        # Log the change
        log = ChangeLog(
            action='freeze' if new_frozen_state else 'unfreeze',
            entity_type='task',
            entity_id=task.id,
            old_value=json.dumps(old_value),
            new_value=json.dumps(task.to_dict())
        )
        db.session.add(log)

    db.session.commit()

    return jsonify({
        'success': True,
        'count': len(tasks_on_day),
        'frozen': new_frozen_state
    })


@app.route('/api/tasks/reorder', methods=['POST'])
@login_required
def reorder_tasks():
    data = request.json
    task_ids = data.get('task_ids', [])

    # Update priorities based on order (higher index = higher priority)
    for index, task_id in enumerate(reversed(task_ids)):
        task = Task.query.get(task_id)
        if task:
            old_priority = task.priority
            task.priority = index
            db.session.commit()

            # Log the reorder
            log = ChangeLog(
                action='reorder',
                entity_type='task',
                entity_id=task.id,
                old_value=json.dumps({'priority': old_priority}),
                new_value=json.dumps({'priority': task.priority})
            )
            db.session.add(log)

    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/schedule', methods=['POST'])
@login_required
def auto_schedule():
    # Get all incomplete tasks
    tasks = Task.query.filter_by(completed=False).order_by(Task.priority.desc(), Task.deadline.asc()).all()

    # Get external calendar events
    external_events = []
    calendar_sources = CalendarSource.query.filter_by(enabled=True).all()
    for source in calendar_sources:
        events = fetch_external_events(source.ics_url)
        external_events.extend(events)
        source.last_fetched = datetime.utcnow()

    db.session.commit()

    # Get spaces and their constraints
    spaces = Space.query.all()
    space_constraints = {space.name: space.get_time_constraints() for space in spaces}

    # Schedule tasks
    scheduled_tasks = schedule_tasks(tasks, external_events, space_constraints)

    # Update tasks with scheduled times
    for task_data in scheduled_tasks:
        task = Task.query.get(task_data['id'])
        if task:
            task.scheduled_start = task_data['scheduled_start']
            task.scheduled_end = task_data['scheduled_end']

    db.session.commit()

    return jsonify({'success': True, 'scheduled_tasks': len(scheduled_tasks)})


# Space endpoints
@app.route('/api/spaces', methods=['GET'])
@login_required
def get_spaces():
    spaces = Space.query.all()
    return jsonify([space.to_dict() for space in spaces])


@app.route('/api/spaces', methods=['POST'])
@login_required
def create_space():
    data = request.json

    space = Space(
        name=data['name'],
        description=data.get('description', '')
    )
    space.set_time_constraints(data.get('time_constraints', []))

    db.session.add(space)
    db.session.commit()

    return jsonify(space.to_dict()), 201


@app.route('/api/spaces/<int:space_id>', methods=['PUT'])
@login_required
def update_space(space_id):
    space = Space.query.get_or_404(space_id)
    data = request.json

    if 'name' in data:
        space.name = data['name']
    if 'description' in data:
        space.description = data['description']
    if 'time_constraints' in data:
        space.set_time_constraints(data['time_constraints'])

    db.session.commit()
    return jsonify(space.to_dict())


@app.route('/api/spaces/<int:space_id>', methods=['DELETE'])
@login_required
def delete_space(space_id):
    space = Space.query.get_or_404(space_id)
    db.session.delete(space)
    db.session.commit()
    return jsonify({'success': True})


# Calendar source endpoints
@app.route('/api/calendar-sources', methods=['GET'])
@login_required
def get_calendar_sources():
    sources = CalendarSource.query.all()
    return jsonify([source.to_dict() for source in sources])


@app.route('/api/calendar-sources', methods=['POST'])
@login_required
def create_calendar_source():
    data = request.json

    source = CalendarSource(
        name=data['name'],
        ics_url=data['ics_url'],
        enabled=data.get('enabled', True)
    )

    db.session.add(source)
    db.session.commit()

    return jsonify(source.to_dict()), 201


@app.route('/api/calendar-sources/<int:source_id>', methods=['DELETE'])
@login_required
def delete_calendar_source(source_id):
    source = CalendarSource.query.get_or_404(source_id)
    db.session.delete(source)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/external-events', methods=['GET'])
@login_required
def get_external_events():
    all_events = []
    sources = CalendarSource.query.filter_by(enabled=True).all()

    for source in sources:
        events = fetch_external_events(source.ics_url)
        # Convert datetime objects to ISO format strings for JSON serialization
        for event in events:
            if isinstance(event.get('start'), datetime):
                event['start'] = event['start'].isoformat()
            if isinstance(event.get('end'), datetime):
                event['end'] = event['end'].isoformat()
        all_events.extend(events)

    return jsonify(all_events)


# Change log endpoints
@app.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    limit = request.args.get('limit', 100, type=int)
    logs = ChangeLog.query.order_by(ChangeLog.timestamp.desc()).limit(limit).all()
    return jsonify([log.to_dict() for log in logs])


# Initialize database
with app.app_context():
    db.create_all()

    # Create default spaces if they don't exist
    if Space.query.count() == 0:
        default_spaces = [
            {'name': 'work', 'description': 'Work-related tasks, meetings, and projects during office hours', 'constraints': [
                {'day': 1, 'start': '09:00', 'end': '17:00'},
                {'day': 2, 'start': '09:00', 'end': '17:00'},
                {'day': 3, 'start': '09:00', 'end': '17:00'},
                {'day': 4, 'start': '09:00', 'end': '17:00'},
                {'day': 5, 'start': '09:00', 'end': '17:00'}
            ]},
            {'name': 'study', 'description': 'Learning activities, courses, homework, and educational tasks', 'constraints': []},
            {'name': 'association', 'description': 'Community group, club, or volunteer organization activities', 'constraints': [
                {'day': 3, 'start': '18:00', 'end': '22:00'}
            ]}
        ]

        for space_data in default_spaces:
            space = Space(name=space_data['name'], description=space_data['description'])
            space.set_time_constraints(space_data['constraints'])
            db.session.add(space)

        db.session.commit()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=53000, debug=True)
