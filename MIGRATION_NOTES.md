# Migration to Space ID and Multiple Task Parsing

## Summary of Changes

This update improves the way spaces and tasks are handled by the AI parser:

1. **Space ID Usage**: The AI now receives and returns space IDs instead of space names for more robust data integrity
2. **Multiple Task Support**: The AI can now return multiple tasks from a single input when appropriate
3. **Time-Based Priority**: AI computes time remaining until deadline and adjusts priority accordingly
4. **Current Time Context**: AI receives current date and time (not just date) for better deadline calculation
5. **Database Schema Update**: Added `space_id` foreign key column to tasks table

## Changes Made

### 1. Database Model (`models.py`)
- Added `space_id` column with foreign key to `spaces` table
- Added `space_rel` relationship for easy access to Space object
- Updated `to_dict()` method to include both `space` (name) and `space_id` for backward compatibility
- Kept old `space` (name) field for backward compatibility during transition

### 2. AI Prompt (`prompt.md`)
- Updated to instruct AI to return `space_id` (numeric) instead of `space` (string)
- Added support for returning multiple tasks as a JSON array
- Emphasized preference for single task unless input clearly describes multiple distinct tasks
- Added time-based priority adjustment guidelines:
  - Computes time remaining to deadline
  - Adjusts priority based on urgency (<3 hours = 9-10, 3-24 hours = 7-9, etc.)
  - Combines with urgency keywords for final priority
- Added example showing multiple task output format
- Updated all examples to use `space_id`

### 3. AI Parser (`ai_parser.py`)
- Modified `parse_task_with_ai()` to return a list of tasks instead of a single task
- Updated to send current date and time (not just date) to AI for better context
- Updated to handle both single task objects and arrays from AI response
- Updated fallback logic to return list with `space_id` field
- Updated docstring to reflect new behavior

### 4. API Endpoints (`app.py`)

#### `/api/tasks/parse` (AI Task Parsing)
- Updated to include space IDs in system prompt sent to AI
- Modified to handle list of tasks returned by parser
- Creates multiple tasks when AI returns multiple tasks
- Returns single task object or array of tasks for backward compatibility

#### `/api/tasks` (POST - Manual Task Creation)
- Updated to support both `space_id` (new) and `space` (deprecated) fields
- Automatically resolves space name to space_id if only name provided

#### `/api/tasks/<id>` (PUT - Task Update)
- Added support for updating `space_id` field

### 5. Migration Script (`migrate_to_space_id.py`)
- New script to add `space_id` column to existing database
- Populates `space_id` values from existing `space` names
- Safe to run multiple times (idempotent)
- Provides migration statistics

## Backward Compatibility

The changes maintain backward compatibility:

- Old `space` field (name) is kept in database
- Task API responses include both `space` (name) and `space_id`
- Manual task creation accepts both `space` and `space_id`
- Scheduler continues to work with space names

## Migration Steps

1. **Deploy Code**: Update all files with new code
2. **Run Migration**: Execute `python migrate_to_space_id.py`
3. **Verify**: Check that tasks have `space_id` values populated

## Testing Checklist

- [x] Python syntax check passes
- [ ] Application starts without errors
- [ ] Migration script runs successfully
- [ ] AI parsing returns space_id instead of space name
- [ ] Single task parsing works correctly
- [ ] Multiple task parsing works correctly
- [ ] Manual task creation with space_id works
- [ ] Task updates with space_id work
- [ ] Scheduler continues to work correctly
- [ ] Task list displays correctly in UI

## API Changes

### Request Changes
**POST /api/tasks** now accepts:
```json
{
  "title": "Task title",
  "space_id": 1  // New: numeric space ID (preferred)
  // "space": "work"  // Old: still supported for backward compatibility
}
```

### Response Changes
**All task endpoints** now return:
```json
{
  "id": 1,
  "title": "Task title",
  "space": "work",  // Name for backward compatibility
  "space_id": 1,    // New: numeric ID
  ...
}
```

**POST /api/tasks/parse** may now return:
- Single task object (existing behavior)
- Array of task objects (new behavior when multiple tasks detected)

## AI Behavior Changes

### Input to AI
**Before:**
```
Available spaces:
- work: Work-related tasks, meetings, and projects
- study: Learning activities, courses, homework
```

**After:**
```
Available spaces:
- ID: 1, Name: work, Description: Work-related tasks, meetings, and projects
- ID: 2, Name: study, Description: Learning activities, courses, homework
```

### Output from AI
**Before (single task only):**
```json
{
  "title": "Task title",
  "space": "work",
  ...
}
```

**After (single or multiple):**
```json
{
  "title": "Task title",
  "space_id": 1,
  ...
}
```

Or for multiple tasks:
```json
[
  {"title": "Task 1", "space_id": 1, ...},
  {"title": "Task 2", "space_id": 1, ...}
]
```

## Notes

- The AI will prefer returning a single task and only split into multiple when obvious
- Space names are still visible in UI for user-friendliness
- Database integrity improved with foreign key constraint
- Future updates can gradually deprecate the old `space` name field
