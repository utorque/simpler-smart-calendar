#!/usr/bin/env python3
"""
Migration script to add space_id column to tasks table and populate it
from existing space names.

Run this script after deploying the code changes to migrate existing data.

Usage:
    python migrate_to_space_id.py
"""

from app import app, db
from models import Task, Space
from sqlalchemy import text


def migrate():
    """Migrate existing tasks to use space_id instead of space name."""

    with app.app_context():
        print("Starting migration: Adding space_id column to tasks...")

        # Check if space_id column already exists
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('tasks')]

        if 'space_id' not in columns:
            print("Adding space_id column to tasks table...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE tasks ADD COLUMN space_id INTEGER'))
                conn.commit()
            print("✓ Column added")
        else:
            print("✓ space_id column already exists")

        # Populate space_id from space names
        print("\nPopulating space_id values from space names...")
        tasks = Task.query.all()
        spaces_cache = {space.name: space.id for space in Space.query.all()}

        updated_count = 0
        for task in tasks:
            if task.space and not task.space_id:
                space_id = spaces_cache.get(task.space)
                if space_id:
                    task.space_id = space_id
                    updated_count += 1
                else:
                    print(f"  Warning: Space '{task.space}' not found for task {task.id}")

        if updated_count > 0:
            db.session.commit()
            print(f"✓ Updated {updated_count} tasks with space_id")
        else:
            print("✓ No tasks needed updating")

        # Report statistics
        print("\nMigration Statistics:")
        total_tasks = Task.query.count()
        tasks_with_space_id = Task.query.filter(Task.space_id.isnot(None)).count()
        tasks_with_space_name = Task.query.filter(Task.space.isnot(None)).count()

        print(f"  Total tasks: {total_tasks}")
        print(f"  Tasks with space_id: {tasks_with_space_id}")
        print(f"  Tasks with space name: {tasks_with_space_name}")

        print("\n✓ Migration completed successfully!")


if __name__ == '__main__':
    print("=" * 60)
    print("Database Migration: Add space_id to tasks")
    print("=" * 60)
    print()

    response = input("This will modify your database. Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        migrate()
    else:
        print("Migration cancelled.")
