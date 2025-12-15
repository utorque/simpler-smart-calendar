from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
from models import db, Task, Location, ChangeLog, CalendarSource
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
        location=data.get('location'),
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

    try:
        task_data = parse_task_with_ai(text, app.config['OPENAI_API_KEY'])

        task = Task(
            title=task_data['title'],
            description=task_data.get('description'),
            location=task_data.get('location'),
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    if 'location' in data:
        task.location = data['location']
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
    try:
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

        # Get locations and their constraints
        locations = Location.query.all()
        location_constraints = {loc.name: loc.get_time_constraints() for loc in locations}

        # Schedule tasks
        scheduled_tasks = schedule_tasks(tasks, external_events, location_constraints)

        # Update tasks with scheduled times
        for task_data in scheduled_tasks:
            task = Task.query.get(task_data['id'])
            if task:
                task.scheduled_start = task_data['scheduled_start']
                task.scheduled_end = task_data['scheduled_end']

        db.session.commit()

        return jsonify({'success': True, 'scheduled_tasks': len(scheduled_tasks)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Location endpoints
@app.route('/api/locations', methods=['GET'])
@login_required
def get_locations():
    locations = Location.query.all()
    return jsonify([loc.to_dict() for loc in locations])


@app.route('/api/locations', methods=['POST'])
@login_required
def create_location():
    data = request.json

    location = Location(
        name=data['name']
    )
    location.set_time_constraints(data.get('time_constraints', []))

    db.session.add(location)
    db.session.commit()

    return jsonify(location.to_dict()), 201


@app.route('/api/locations/<int:location_id>', methods=['PUT'])
@login_required
def update_location(location_id):
    location = Location.query.get_or_404(location_id)
    data = request.json

    if 'name' in data:
        location.name = data['name']
    if 'time_constraints' in data:
        location.set_time_constraints(data['time_constraints'])

    db.session.commit()
    return jsonify(location.to_dict())


@app.route('/api/locations/<int:location_id>', methods=['DELETE'])
@login_required
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    db.session.delete(location)
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
    try:
        all_events = []
        sources = CalendarSource.query.filter_by(enabled=True).all()

        for source in sources:
            events = fetch_external_events(source.ics_url)
            all_events.extend(events)

        return jsonify(all_events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

    # Create default locations if they don't exist
    if Location.query.count() == 0:
        default_locations = [
            {'name': 'work', 'constraints': [
                {'day': 1, 'start': '09:00', 'end': '17:00'},
                {'day': 2, 'start': '09:00', 'end': '17:00'},
                {'day': 3, 'start': '09:00', 'end': '17:00'},
                {'day': 4, 'start': '09:00', 'end': '17:00'},
                {'day': 5, 'start': '09:00', 'end': '17:00'}
            ]},
            {'name': 'study', 'constraints': []},
            {'name': 'association', 'constraints': [
                {'day': 3, 'start': '18:00', 'end': '22:00'}
            ]}
        ]

        for loc_data in default_locations:
            loc = Location(name=loc_data['name'])
            loc.set_time_constraints(loc_data['constraints'])
            db.session.add(loc)

        db.session.commit()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
