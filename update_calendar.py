import re
import uuid
import hashlib
import requests
import json
import os
from config import CALENDAR_URL, LANGUAGE

# Fetch the calendar data from the URL
response = requests.get(CALENDAR_URL)
data = response.text

# Split data into lines
lines = data.split('\n')

# Initialize variables
corrected_events = []
in_event = False
event_lines = []

# Translation mappings
translations = {
    'PL': {
        'wykład': 'wykład',
        'ćwiczenia': 'ćwiczenia',
        'egzamin': 'egzamin',
        'Paw.': 'Paw.',
        'Bud.gł.': 'Bud.gł.',
        'sala': 'sala',
        'lab.': 'lab.',
        'prof. UEK dr hab.': 'prof. UEK dr hab.',
        'dr hab.': 'dr hab.',
        'dr': 'dr',
        'mgr': 'mgr',
    },
    'EN': {
        'wykład': 'Lecture',
        'ćwiczenia': 'Class',
        'egzamin': 'Exam',
        'Paw.': 'Building ',
        'Bud.gł.': 'Main Building',
        'sala': 'Room',
        'lab.': 'Lab',
        'prof. UEK dr hab.': 'Prof. UEK Dr hab.',
        'dr hab.': 'Dr hab.',
        'dr': 'Dr',
        'mgr': 'MSc',
    }
}

# Choose the appropriate translation mapping
translation_map = translations.get(LANGUAGE, translations['PL'])

# Load UID mappings from file
uid_mappings_file = 'uid_mappings.json'
if os.path.exists(uid_mappings_file):
    with open(uid_mappings_file, 'r', encoding='utf-8') as f:
        uid_mappings = json.load(f)
else:
    uid_mappings = {}

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
            original_summary = event_props.get('SUMMARY', '')  # Store original SUMMARY in Polish
            original_dtstart = event_props.get('DTSTART', '')
            original_dtend = event_props.get('DTEND', '')

            # Generate event key (date and original name in Polish)
            # Extract date from DTSTART (format: YYYYMMDD)
            date_match = re.search(r'(\d{8})T\d{6}', original_dtstart)
            if date_match:
                event_date = date_match.group(1)
            else:
                event_date = 'unknown_date'

            event_key = f"{event_date}_{original_summary}"

            # Check if UID exists in mappings
            if event_key in uid_mappings:
                event_uid = uid_mappings[event_key]
            else:
                # Generate new UID and store it
                event_uid = f'{uuid.uuid4()}@uek.pl'
                uid_mappings[event_key] = event_uid

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

                # Perform translations if necessary
                if LANGUAGE == 'EN':
                    if evt_line.startswith('SUMMARY:'):
                        summary_value = evt_line[len('SUMMARY:'):]
                        # Replace Polish terms in SUMMARY
                        for pl_word, en_word in translation_map.items():
                            summary_value = summary_value.replace(pl_word, en_word)
                        evt_line = 'SUMMARY:' + summary_value
                    elif evt_line.startswith('LOCATION:'):
                        location_value = evt_line[len('LOCATION:'):]
                        # Replace Polish terms in LOCATION
                        for pl_word, en_word in translation_map.items():
                            location_value = location_value.replace(pl_word, en_word)
                        evt_line = 'LOCATION:' + location_value
                    elif evt_line.startswith('DESCRIPTION:'):
                        description_value = evt_line[len('DESCRIPTION:'):]
                        # Replace Polish terms in DESCRIPTION
                        for pl_word, en_word in translation_map.items():
                            description_value = description_value.replace(pl_word, en_word)
                        evt_line = 'DESCRIPTION:' + description_value

                processed_event.append(evt_line)

            # Remove existing UID from processed_event if present
            processed_event = [line for line in processed_event if not line.startswith('UID:')]
            # Insert UID after BEGIN:VEVENT
            processed_event.insert(1, f'UID:{event_uid}')

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

# Include the VTIMEZONE component
vtimezone_component = [
    'BEGIN:VTIMEZONE',
    'TZID:Europe/Warsaw',
    'X-LIC-LOCATION:Europe/Warsaw',
    'BEGIN:DAYLIGHT',
    'TZOFFSETFROM:+0100',
    'TZOFFSETTO:+0200',
    'TZNAME:CEST',
    'DTSTART:19700329T020000',
    'RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU',
    'END:DAYLIGHT',
    'BEGIN:STANDARD',
    'TZOFFSETFROM:+0200',
    'TZOFFSETTO:+0100',
    'TZNAME:CET',
    'DTSTART:19701025T030000',
    'RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU',
    'END:STANDARD',
    'END:VTIMEZONE',
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
all_lines = headers + vtimezone_component + corrected_events + footers
corrected_data = '\r\n'.join(fold_line(line) for line in all_lines)

# Save to a new .ics file
with open('corrected_calendar.ics', 'w', encoding='utf-8') as f:
    f.write(corrected_data)

# Save updated UID mappings to file
with open(uid_mappings_file, 'w', encoding='utf-8') as f:
    json.dump(uid_mappings, f, ensure_ascii=False, indent=2)
