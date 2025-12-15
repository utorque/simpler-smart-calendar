#!/usr/bin/env python3
"""
Database migration script to add the 'frozen' field to existing tasks.

This script safely adds the frozen column to the tasks table if it doesn't exist.
Run this after pulling the task freezing update to upgrade your database.

Usage:
    python migration.py
"""

import sqlite3
import os
import sys
from datetime import datetime


def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate_database(db_path='instance/tasks.db'):
    """Add frozen column to tasks table if it doesn't exist."""

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        print("   No migration needed - database will be created with correct schema on first run.")
        return True

    print(f"📦 Found database at {db_path}")

    # Backup the database first
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Created backup at {backup_path}")
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup: {e}")
        response = input("Continue without backup? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return False

    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("✅ Connected to database")

        # Check if frozen column exists
        if check_column_exists(cursor, 'tasks', 'frozen'):
            print("✅ Column 'frozen' already exists in tasks table")
            print("   No migration needed!")
            conn.close()
            return True

        # Add frozen column
        print("📝 Adding 'frozen' column to tasks table...")
        cursor.execute("""
            ALTER TABLE tasks
            ADD COLUMN frozen BOOLEAN DEFAULT 0
        """)

        # Set all existing tasks to frozen=False (0)
        cursor.execute("""
            UPDATE tasks
            SET frozen = 0
            WHERE frozen IS NULL
        """)

        conn.commit()
        print("✅ Successfully added 'frozen' column")

        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE frozen IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"✅ Verified: {count} tasks now have frozen field set to False")

        conn.close()
        print("\n🎉 Migration completed successfully!")
        print(f"   Backup saved at: {backup_path}")
        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        if 'conn' in locals():
            conn.close()
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if 'conn' in locals():
            conn.close()
        return False


def main():
    """Main migration function."""
    print("=" * 60)
    print("Task Freezing Feature - Database Migration")
    print("=" * 60)
    print()

    # Check for custom database path
    db_path = 'instance/tasks.db'
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        print(f"Using custom database path: {db_path}")

    # Run migration
    success = migrate_database(db_path)

    if success:
        print("\n✅ Your database is ready to use with task freezing!")
        print("\nYou can now:")
        print("  • Ctrl+Click tasks in the calendar to freeze/unfreeze them")
        print("  • Ctrl+Click day headers to freeze/unfreeze all tasks on that day")
        print("  • Frozen tasks won't move when you auto-schedule")
        sys.exit(0)
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
