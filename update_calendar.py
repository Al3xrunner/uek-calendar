import re
import uuid
import requests
from datetime import datetime
from config import CALENDAR_URL

# Fetch the calendar data from the URL
response = requests.get(CALENDAR_URL)
data = response.text

# Split data into lines
lines = data.split('\n')

# Initialize variables
corrected_lines = []
in_event = False
event_lines = []

for line in lines:
    # Start of an event
    if line.strip() == 'BEGIN:VEVENT':
        in_event = True
        event_lines = [line]
        continue
    # End of an event
    if line.strip() == 'END:VEVENT':
        event_lines.append(line)
        in_event = False
        # Check if event should be excluded
        event_str = '\n'.join(event_lines)
        exclude_event = False
        if 'LOCATION:Wybierz swoją grupę językową' in event_str:
            exclude_event = True
        if 'SUMMARY:lektorat | English' in event_str and 'LOCATION:Wybierz swoją grupę językową' in event_str:
            exclude_event = True
        if 'SUMMARY:rezerwacja |' in event_str:
            exclude_event = True
        if 'SUMMARY:Przeniesienie zajęć |' in event_str:
            exclude_event = True
        if exclude_event:
            # Skip adding this event to corrected_lines
            continue
        else:
            # Process and add the event
            processed_event = []
            for evt_line in event_lines:
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
                evt_line = re.sub(r'DTSTART;TZID=Europe/Warsaw:(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})', r'DTSTART;TZID=Europe/Warsaw:\1\2\3T\4\5\6', evt_line)
                evt_line = re.sub(r'DTEND;TZID=Europe/Warsaw:(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})', r'DTEND;TZID=Europe/Warsaw:\1\2\3T\4\5\6', evt_line)
                processed_event.append(evt_line)
            # Add UID to the event
            event_uid = f'{uuid.uuid4()}@uek.pl'
            processed_event.insert(1, f'UID:{event_uid}')
            # Add the processed event to corrected_lines
            corrected_lines.extend(processed_event)
        continue
    if in_event:
        event_lines.append(line)
    else:
        corrected_lines.append(line)

# Ensure correct VCALENDAR headers
if 'BEGIN:VCALENDAR' not in corrected_lines[0]:
    corrected_lines.insert(0, 'BEGIN:VCALENDAR')
if 'VERSION:2.0' not in corrected_lines:
    corrected_lines.insert(1, 'VERSION:2.0')
if 'PRODID:-//Uek Plan zajęć//' not in corrected_lines:
    corrected_lines.insert(2, 'PRODID:-//Uek Plan zajęć//')
if 'END:VCALENDAR' not in corrected_lines[-1]:
    corrected_lines.append('END:VCALENDAR')

# Join corrected lines
corrected_data = '\n'.join(corrected_lines)

# Save to a new .ics file
with open('corrected_calendar.ics', 'w', encoding='utf-8') as f:
    f.write(corrected_data)
