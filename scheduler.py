from datetime import datetime, timedelta


def schedule_tasks(tasks, external_events, space_constraints):
    """
    Schedule tasks based on priority, deadlines, and space constraints.

    Args:
        tasks: List of Task objects to schedule
        external_events: List of external calendar events (dicts with start, end)
        space_constraints: Dict of space names to their time constraints

    Returns:
        List of dicts with task id, scheduled_start, and scheduled_end
    """
    scheduled_tasks = []

    # Sort tasks by priority (descending) and deadline (ascending)
    sorted_tasks = sorted(
        tasks,
        key=lambda t: (
            -t.priority,
            t.deadline if t.deadline else datetime.max,
            t.created_at
        )
    )

    # Start scheduling from now
    current_time = datetime.now()

    # Round to next 30-minute interval
    if current_time.minute < 30:
        current_time = current_time.replace(minute=30, second=0, microsecond=0)
    else:
        current_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    # Create list of busy time slots from external events
    busy_slots = []
    for event in external_events:
        busy_slots.append({
            'start': event['start'],
            'end': event['end']
        })

    for task in sorted_tasks:
        duration = timedelta(minutes=task.estimated_duration or 60)
        deadline = task.deadline

        # Find next available slot for this task
        slot_start = find_next_available_slot(
            current_time,
            duration,
            busy_slots,
            task.space,
            space_constraints,
            deadline
        )

        if slot_start:
            slot_end = slot_start + duration

            scheduled_tasks.append({
                'id': task.id,
                'scheduled_start': slot_start,
                'scheduled_end': slot_end
            })

            # Add this task to busy slots for future scheduling
            busy_slots.append({
                'start': slot_start,
                'end': slot_end
            })

            # Sort busy slots to maintain order
            busy_slots.sort(key=lambda x: x['start'])

    return scheduled_tasks


def find_next_available_slot(start_time, duration, busy_slots, space, space_constraints, deadline=None):
    """
    Find the next available time slot that satisfies all constraints.

    Args:
        start_time: datetime to start searching from
        duration: timedelta of task duration
        busy_slots: List of busy time slots
        space: Task space name
        space_constraints: Dict of space constraints
        deadline: Optional deadline datetime

    Returns:
        datetime of slot start, or None if no suitable slot found
    """
    current = start_time
    max_search_days = 90  # Search up to 90 days ahead

    # If there's a deadline, don't schedule beyond it
    if deadline:
        max_search_time = deadline - duration
    else:
        max_search_time = start_time + timedelta(days=max_search_days)

    while current < max_search_time:
        slot_end = current + duration

        # Check if this slot is within space constraints
        if not is_within_space_constraints(current, slot_end, space, space_constraints):
            # Move to next valid time for this space
            current = get_next_valid_time_for_space(current, space, space_constraints)
            if current is None:
                # No valid time found within space constraints
                return None
            continue

        # Check if this slot conflicts with any busy slot
        is_available = True
        for busy in busy_slots:
            if slots_overlap(current, slot_end, busy['start'], busy['end']):
                is_available = False
                # Move to end of this busy slot
                current = busy['end']
                # Round to next 30-minute interval
                if current.minute < 30:
                    current = current.replace(minute=30, second=0, microsecond=0)
                else:
                    current = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                break

        if is_available:
            return current

        # If no conflict but still didn't return, move forward
        current += timedelta(minutes=30)

    return None


def slots_overlap(start1, end1, start2, end2):
    """Check if two time slots overlap."""
    return start1 < end2 and end1 > start2


def is_within_space_constraints(start, end, space, space_constraints):
    """
    Check if a time slot is within the constraints for a given space.

    Space constraints format:
    {
        'space_name': [
            {'day': 1, 'start': '09:00', 'end': '17:00'},  # Monday
            {'day': 3, 'start': '18:00', 'end': '22:00'}   # Wednesday
        ]
    }

    day: 0=Monday, 1=Tuesday, ..., 6=Sunday
    """
    if not space or space not in space_constraints:
        # No constraints, any time is fine
        return True

    constraints = space_constraints[space]

    if not constraints or len(constraints) == 0:
        # No constraints for this space
        return True

    # Check if the time slot falls within any of the allowed time windows
    for constraint in constraints:
        day_of_week = constraint['day']
        start_time_str = constraint['start']
        end_time_str = constraint['end']

        # Check if the slot's day matches
        if start.weekday() == day_of_week:
            # Parse constraint times
            start_hour, start_minute = map(int, start_time_str.split(':'))
            end_hour, end_minute = map(int, end_time_str.split(':'))

            constraint_start = start.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            constraint_end = start.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)

            # Check if the slot fits within this constraint
            if start >= constraint_start and end <= constraint_end:
                return True

    return False


def get_next_valid_time_for_space(current, space, space_constraints):
    """
    Get the next valid time for a space based on its constraints.
    """
    if not space or space not in space_constraints:
        return current

    constraints = space_constraints[space]

    if not constraints or len(constraints) == 0:
        return current

    # Try to find a valid time within the next 90 days
    for days_ahead in range(90):
        check_time = current + timedelta(days=days_ahead)

        for constraint in constraints:
            if check_time.weekday() == constraint['day']:
                start_hour, start_minute = map(int, constraint['start'].split(':'))
                constraint_start = check_time.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)

                if constraint_start >= current:
                    return constraint_start

    return None
