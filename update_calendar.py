import re
import uuid
import requests
from config import CALENDAR_URL

# Fetch the calendar data from the URL
response = requests.get(CALENDAR_URL)
data = response.text

# Split data into lines
lines = data.split('\n')

# Initialize variables
corrected_events = []
in_event = False
event_lines = []

for line in lines:
    line = line.rstrip('\r\n')
    # Start of an event
    if line.strip() == 'BEGIN:VEVENT':
        in_event = True
        event_lines = [line]
        continue
    # End of an event
    elif line.strip() == 'END:VEVENT':
        event_lines.append(line)
        in_event = False
        # Process the event
        # Unfold lines (concatenate continuation lines)
        unfolded_event = []
        previous_line = ''
        for evt_line in event_lines:
            if evt_line.startswith(' '):
                previous_line += evt_line[1:]
            else:
                if previous_line:
                    unfolded_event.append(previous_line)
                previous_line = evt_line
        if previous_line:
            unfolded_event.append(previous_line)
        # Parse event properties
        event_props = {}
        for evt_line in unfolded_event:
            if ':' in evt_line:
                key, value = evt_line.split(':', 1)
                event_props[key] = value
        # Check for placeholder text
        summary = event_props.get('SUMMARY', '')
        location = event_props.get('LOCATION', '')
        exclude_event = False
        if 'Wybierz swoją grupę językową' in location:
            exclude_event = True
        elif 'lektorat |' in summary and 'Wybierz swoją grupę językową' in location:
            exclude_event = True
        elif 'rezerwacja |' in summary:
            exclude_event = True
        elif 'Przeniesienie zajęć |' in summary:
            exclude_event = True
        if exclude_event:
            # Skip this event
            continue
        else:
            # Correct event properties
            processed_event = []
            for evt_line in unfolded_event:
                # Remove ;VALUE=DATE-TIME from DTSTART and DTEND
                evt_line = re.sub(r'(DTSTART|DTEND);[^:]*:', r'\1:', evt_line)
                # Correct DTSTAMP format
                evt_line = re.sub(r'DTSTAMP;[^:]*:(.*)', r'DTSTAMP:\1', evt_line)
                # Add timezone to DTSTART and DTEND if missing
                if evt_line.startswith('DTSTART:') or evt_line.startswith('DTEND:'):
                    if 'TZID=Europe/Warsaw' not in evt_line:
                        evt_line = evt_line.replace('DTSTART:', 'DTSTART;TZID=Europe/Warsaw:')
                        evt_line = evt_line.replace('DTEND:', 'DTEND;TZID=Europe/Warsaw:')
                # Correct date formats if necessary
                evt_line = re.sub(r'DTSTART;TZID=Europe/Warsaw:(\d{8}T\d{6})', r'DTSTART;TZID=Europe/Warsaw:\1', evt_line)
                evt_line = re.sub(r'DTEND;TZID=Europe/Warsaw:(\d{8}T\d{6})', r'DTEND;TZID=Europe/Warsaw:\1', evt_line)
                processed_event.append(evt_line)
            # Add UID to the event
            event_uid = f'{uuid.uuid4()}@uek.pl'
            # Insert UID after BEGIN:VEVENT
            processed_event.insert(1, f'UID:{event_uid}')
            # Add BEGIN:VEVENT and END:VEVENT
            processed_event.insert(0, 'BEGIN:VEVENT')
            processed_event.append('END:VEVENT')
            # Add the processed event to corrected_events
            corrected_events.extend(processed_event)
    elif in_event:
        event_lines.append(line)
    else:
        # Collect non-event lines (headers and footers)
        continue

# Prepare the final corrected lines
headers = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Uek Plan zajęć//',
]
footers = ['END:VCALENDAR']

# Function to fold lines longer than 75 octets
def fold_line(line):
    if len(line.encode('utf-8')) <= 75:
        return line
    else:
        folded = ''
        while len(line.encode('utf-8')) > 75:
            part = line[:75]
            # Ensure we are not splitting multi-byte characters
            while len(part.encode('utf-8')) > 75:
                part = part[:-1]
            folded += part + '\r\n '
            line = line[len(part):]
        folded += line
        return folded

# Apply line folding to all lines
all_lines = headers + corrected_events + footers
corrected_data = '\r\n'.join(fold_line(line) for line in all_lines)

# Save to a new .ics file
with open('corrected_calendar.ics', 'w', encoding='utf-8') as f:
    f.write(corrected_data)
