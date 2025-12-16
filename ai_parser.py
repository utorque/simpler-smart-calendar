from anthropic import Anthropic
import json
from datetime import datetime, timedelta


def parse_task_with_ai(text, api_key, system_prompt):
    """
    Parse a text input using Anthropic Claude to extract task information.

    Returns a list of task dictionaries. Each dictionary contains:
    - title: Task title
    - description: Task description
    - space_id: Space ID (numeric) or None
    - priority: Priority level (0-10)
    - deadline: ISO format datetime string or None
    - estimated_duration: Duration in minutes

    Note: The AI may return multiple tasks if the input clearly describes
    multiple distinct tasks, but will prefer returning a single task.
    """
    if not api_key:
        # Fallback to simple parsing if no API key
        return [{
            'title': text[:100],
            'description': text,
            'space_id': None,
            'priority': 5,
            'deadline': None,
            'estimated_duration': 60
        }]

    client = Anthropic(api_key=api_key)

    # Add current date and time to the user message for context
    now = datetime.now()
    user_message = f"Current date and time: {now.strftime('%Y-%m-%d %H:%M')}.\n\nTask to parse:\n{text}"

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
        temperature=0.3,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    # Extract text from response
    response_text = response.content[0].text

    # Try to extract JSON from the response
    # Sometimes Claude might include markdown code blocks
    if '```json' in response_text:
        json_start = response_text.find('```json') + 7
        json_end = response_text.find('```', json_start)
        response_text = response_text[json_start:json_end].strip()
    elif '```' in response_text:
        json_start = response_text.find('```') + 3
        json_end = response_text.find('```', json_start)
        response_text = response_text[json_start:json_end].strip()

    result = json.loads(response_text)

    # Handle both single task and multiple tasks
    # If result is a dict (single task), convert to list
    if isinstance(result, dict):
        tasks = [result]
    else:
        tasks = result

    # Process deadline for each task - convert relative dates to absolute
    for task in tasks:
        if task.get('deadline'):
            deadline_str = task['deadline'].lower()
            now = datetime.now()

            if 'tomorrow' in deadline_str:
                deadline = now + timedelta(days=1)
                deadline = deadline.replace(hour=23, minute=59, second=0, microsecond=0)
            elif 'next week' in deadline_str:
                deadline = now + timedelta(weeks=1)
                deadline = deadline.replace(hour=23, minute=59, second=0, microsecond=0)
            elif 'next' in deadline_str and 'monday' in deadline_str:
                days_ahead = 7 - now.weekday()
                deadline = now + timedelta(days=days_ahead)
                deadline = deadline.replace(hour=23, minute=59, second=0, microsecond=0)
            elif 'next' in deadline_str and 'friday' in deadline_str:
                days_ahead = (4 - now.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                deadline = now + timedelta(days=days_ahead)
                deadline = deadline.replace(hour=23, minute=59, second=0, microsecond=0)
            else:
                deadline = datetime.fromisoformat(task['deadline'].replace('Z', '+00:00'))

            if deadline:
                task['deadline'] = deadline.isoformat()

    return tasks
