from openai import OpenAI
import json
from datetime import datetime, timedelta


def parse_task_with_ai(text, api_key):
    """
    Parse a text input using OpenAI to extract task information.

    Returns a dictionary with:
    - title: Task title
    - description: Task description
    - location: Task location (work, study, association, etc.)
    - priority: Priority level (0-10)
    - deadline: ISO format datetime string or None
    - estimated_duration: Duration in minutes
    """
    if not api_key:
        # Fallback to simple parsing if no API key
        return {
            'title': text[:100],
            'description': text,
            'location': 'general',
            'priority': 5,
            'deadline': None,
            'estimated_duration': 60
        }

    client = OpenAI(api_key=api_key)

    system_prompt = """You are a task parsing assistant for an ADHD-friendly task manager.
Extract task information from the user's input and return a JSON object with the following fields:
- title: A clear, concise task title (max 100 chars)
- description: Full task description
- location: One of: work, study, association, personal, or another appropriate category
- priority: 0-10, where 10 is highest priority. Base this on urgency words (urgent, important, asap, etc.)
- deadline: ISO format datetime string if mentioned, or null. If only a date is mentioned, set time to 23:59. If relative time like "tomorrow" or "next week", calculate from today.
- estimated_duration: Estimated duration in minutes (default 60 if not specified)

Today's date is: """ + datetime.now().strftime('%Y-%m-%d') + """

Examples:
Input: "Finish the presentation for tomorrow's meeting at work, should take about 2 hours"
Output: {"title": "Finish presentation for meeting", "description": "Finish the presentation for tomorrow's meeting at work", "location": "work", "priority": 8, "deadline": "tomorrow at 23:59", "estimated_duration": 120}

Input: "Study for exam next Friday, very important"
Output: {"title": "Study for exam", "description": "Study for exam next Friday, very important", "location": "study", "priority": 9, "deadline": "next Friday at 23:59", "estimated_duration": 180}

Return ONLY the JSON object, no other text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )

        result = json.loads(response.choices[0].message.content)

        # Process deadline - convert relative dates to absolute
        if result.get('deadline'):
            deadline_str = result['deadline'].lower()
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
                try:
                    deadline = datetime.fromisoformat(result['deadline'].replace('Z', '+00:00'))
                except:
                    deadline = None

            if deadline:
                result['deadline'] = deadline.isoformat()

        return result

    except Exception as e:
        print(f"Error parsing with AI: {e}")
        # Fallback to simple parsing
        return {
            'title': text[:100],
            'description': text,
            'location': 'general',
            'priority': 5,
            'deadline': None,
            'estimated_duration': 60
        }
