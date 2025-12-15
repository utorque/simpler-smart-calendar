#!/usr/bin/env python3
"""
Migration script to rename 'locations' to 'spaces' in the database.

This script:
1. Renames the 'locations' table to 'spaces'
2. Renames the 'location' column in 'tasks' table to 'space'
3. Adds the 'description' column to the 'spaces' table
4. Updates change_logs entity_type from 'location' to 'space'

Run this script before starting the updated application if you have existing data.
"""

import sqlite3
import os
import sys

DB_PATH = 'tasks.db'

def migrate_database():
    """Perform database migration from locations to spaces."""

    if not os.path.exists(DB_PATH):
        print(f"Database file '{DB_PATH}' not found.")
        print("No migration needed. The app will create the new schema on first run.")
        return True

    print(f"Found existing database: {DB_PATH}")
    print("Starting migration...")

    try:
        # Create backup
        backup_path = f"{DB_PATH}.backup"
        print(f"Creating backup at {backup_path}...")
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print("Backup created successfully!")

        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if locations table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='locations'")
        if cursor.fetchone() is None:
            print("'locations' table not found. Migration may have already been applied.")
            conn.close()
            return True

        print("Step 1: Renaming 'locations' table to 'spaces'...")
        cursor.execute("ALTER TABLE locations RENAME TO spaces")

        print("Step 2: Adding 'description' column to 'spaces' table...")
        try:
            cursor.execute("ALTER TABLE spaces ADD COLUMN description TEXT")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  - 'description' column already exists, skipping...")
            else:
                raise

        print("Step 3: Creating new tasks table with 'space' column...")
        # Create new tasks table with space column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks_new (
                id INTEGER PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                space VARCHAR(100),
                priority INTEGER DEFAULT 0,
                deadline DATETIME,
                estimated_duration INTEGER,
                scheduled_start DATETIME,
                scheduled_end DATETIME,
                completed BOOLEAN DEFAULT 0,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)

        # Copy data from old tasks table to new one
        cursor.execute("""
            INSERT INTO tasks_new
            SELECT id, title, description, location as space, priority, deadline,
                   estimated_duration, scheduled_start, scheduled_end, completed,
                   created_at, updated_at
            FROM tasks
        """)

        # Drop old tasks table and rename new one
        cursor.execute("DROP TABLE tasks")
        cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")

        print("Step 4: Updating change_logs entity_type from 'location' to 'space'...")
        cursor.execute("UPDATE change_logs SET entity_type = 'space' WHERE entity_type = 'location'")

        # Commit changes
        conn.commit()
        conn.close()

        print("\n✅ Migration completed successfully!")
        print(f"   Backup saved at: {backup_path}")
        print("\nYou can now start the application with the updated code.")
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"   Your original database is backed up at: {backup_path}")
        print("   Please restore from backup if needed.")
        return False

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)
