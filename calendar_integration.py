import requests
from icalendar import Calendar
from datetime import datetime, timedelta


def fetch_external_events(ics_url, days_ahead=30):
    """
    Fetch events from an external ICS calendar URL.

    Args:
        ics_url: URL to the ICS calendar
        days_ahead: Number of days ahead to fetch events for

    Returns:
        List of event dicts with start, end, title, and description
    """
    try:
        response = requests.get(ics_url, timeout=10)
        response.raise_for_status()

        cal = Calendar.from_ical(response.content)

        events = []
        now = datetime.now()
        end_date = now + timedelta(days=days_ahead)

        for component in cal.walk():
            if component.name == "VEVENT":
                start = component.get('dtstart')
                end = component.get('dtend')
                summary = component.get('summary')
                description = component.get('description')

                if start and end:
                    # Convert to datetime if needed
                    start_dt = start.dt if hasattr(start, 'dt') else start
                    end_dt = end.dt if hasattr(end, 'dt') else end

                    # Handle date-only events (convert to datetime)
                    if not isinstance(start_dt, datetime):
                        start_dt = datetime.combine(start_dt, datetime.min.time())
                    if not isinstance(end_dt, datetime):
                        end_dt = datetime.combine(end_dt, datetime.min.time())

                    # Make timezone naive for easier comparison
                    if start_dt.tzinfo:
                        start_dt = start_dt.replace(tzinfo=None)
                    if end_dt.tzinfo:
                        end_dt = end_dt.replace(tzinfo=None)

                    # Only include events within our time range
                    if start_dt < end_date and end_dt > now:
                        events.append({
                            'start': start_dt,
                            'end': end_dt,
                            'title': str(summary) if summary else 'Untitled Event',
                            'description': str(description) if description else '',
                            'source': 'external'
                        })

        return events

    except Exception as e:
        print(f"Error fetching external calendar: {e}")
        return []
