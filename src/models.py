from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    space = db.Column(db.String(100))  # DEPRECATED: kept for backward compatibility, use space_id instead
    space_id = db.Column(db.Integer, db.ForeignKey('spaces.id'))  # Reference to Space table
    priority = db.Column(db.Integer, default=0)  # Higher number = higher priority
    deadline = db.Column(db.DateTime)
    estimated_duration = db.Column(db.Integer)  # in minutes
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)
    completed = db.Column(db.Boolean, default=False)
    frozen = db.Column(db.Boolean, default=False)  # Prevents rescheduling when True
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to Space
    space_rel = db.relationship('Space', backref='tasks', foreign_keys=[space_id])

    def to_dict(self):
        # Determine space name - use space_rel if available, fallback to old space field
        space_name = None
        if self.space_rel:
            space_name = self.space_rel.name
        elif self.space:
            space_name = self.space

        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'space': space_name,  # For backward compatibility in UI
            'space_id': self.space_id,
            'priority': self.priority,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'estimated_duration': self.estimated_duration,
            'scheduled_start': self.scheduled_start.isoformat() if self.scheduled_start else None,
            'scheduled_end': self.scheduled_end.isoformat() if self.scheduled_end else None,
            'completed': self.completed,
            'frozen': self.frozen,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Space(db.Model):
    __tablename__ = 'spaces'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)  # Plain text description of the space (context, purpose, etc.)
    time_constraints = db.Column(db.Text)  # JSON string of time constraints
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_time_constraints(self):
        if self.time_constraints:
            return json.loads(self.time_constraints)
        return []

    def set_time_constraints(self, constraints):
        self.time_constraints = json.dumps(constraints)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'time_constraints': self.get_time_constraints(),
            'created_at': self.created_at.isoformat()
        }


class ChangeLog(db.Model):
    __tablename__ = 'change_logs'

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)  # create, update, delete, reorder, reschedule
    entity_type = db.Column(db.String(50), nullable=False)  # task, space
    entity_id = db.Column(db.Integer)
    old_value = db.Column(db.Text)  # JSON string
    new_value = db.Column(db.Text)  # JSON string
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'old_value': json.loads(self.old_value) if self.old_value else None,
            'new_value': json.loads(self.new_value) if self.new_value else None,
            'timestamp': self.timestamp.isoformat()
        }


class CalendarSource(db.Model):
    __tablename__ = 'calendar_sources'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ics_url = db.Column(db.String(500), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_fetched = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ics_url': self.ics_url,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat(),
            'last_fetched': self.last_fetched.isoformat() if self.last_fetched else None
        }
