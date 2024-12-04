import re
import uuid
import requests
import json
import os
from config import SCHEDULE_LINKS, LANGUAGE

# Enhanced Translation mappings
translations = {
    'PL': {
        'wykład': 'wykład',
        'ćwiczenia': 'ćwiczenia',
        'egzamin': 'egzamin',
        'lektorat': 'lektorat',
        'język angielski': 'język angielski',
        'język niemiecki': 'język niemiecki',
        'Ćwiczenia e-learningowe': 'Ćwiczenia e-learningowe',
        'Paw.': 'Paw.',
        'Bud.gł.': 'Bud.gł.',
        'sala': 'sala',
        'lab.': 'lab.',
        'prof. UEK dr hab.': 'prof. UEK dr hab.',
        'dr hab.': 'dr hab.',
        'dr': 'dr',
        'mgr': 'mgr',
        'Platforma Moodle': 'Platforma Moodle',
        'Kat. Rach.Fin.': 'Kat. Rach.Fin.',
        'KSB': 'KSB',
    },
    'EN': {
        'wykład': 'Lecture',
        'ćwiczenia': 'Exercises',
        'egzamin': 'Exam',
        'lektorat': 'Language Course',
        'język angielski': 'English Language',
        'język niemiecki': 'German Language',
        'Ćwiczenia e-learningowe': 'E-learning Exercises',
        'Paw.': 'Building ',
        'Bud.gł.': 'Main Building',
        'sala': 'Room',
        'lab.': 'Lab',
        'prof. UEK dr hab.': 'Prof. UEK Dr hab.',
        'dr hab.': 'Dr hab.',
        'dr': 'Dr',
        'mgr': 'MSc',
        'Platforma Moodle': 'Moodle Platform',
        'Kat. Rach.Fin.': 'Accounting and Finance Category',
        'KSB': 'KSB',
    }
}

# Choose the appropriate translation mapping
translation_map = translations.get(LANGUAGE, translations['PL'])

def translate_text(text):
    """
    Translate text based on the translation_map.
    """
    for pl_word, en_word in translation_map.items():
        text = re.sub(r'\b' + re.escape(pl_word) + r'\b', en_word, text, flags=re.IGNORECASE)
    return text

def process_calendar(schedule_name, calendar_url):
    # Load UID mappings from file or create an empty one if not present
    uid_mappings_file = f'uid_mappings_{schedule_name}.json'
    uid_mappings = {}

    if os.path.exists(uid_mappings_file):
        with open(uid_mappings_file, 'r', encoding='utf-8') as f:
            try:
                uid_mappings = json.load(f)
            except json.JSONDecodeError:
                uid_mappings = {}
    else:
        # Create an empty JSON file if it doesn't exist
        with open(uid_mappings_file, 'w', encoding='utf-8') as f:
            json.dump(uid_mappings, f)

    # Fetch the calendar data from the URL
    response = requests.get(calendar_url)
    if response.status_code != 200:
        print(f"Failed to fetch calendar for {schedule_name}. Status code: {response.status_code}")
        return
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
                    key = key.split(';')[0]  # Strip any parameters from the key
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

                # Get the original DTSTART line
                dtstart_line = next((line for line in unfolded_event if line.startswith('DTSTART')), '')
                if dtstart_line:
                    dtstart_match = re.search(r'DTSTART(?:;[^:]*)?:(\d{8})T\d{6}', dtstart_line)
                    if dtstart_match:
                        event_date = dtstart_match.group(1)  # YYYYMMDD
                    else:
                        event_date = 'unknown_date'
                else:
                    event_date = 'unknown_date'

                # Normalize the summary by stripping whitespace and converting to lowercase
                event_name = original_summary.strip().lower()

                # Use only date and event name as key
                event_key = f"{event_date}_{event_name}"

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
                    # Remove ;VALUE=DATE-TIME from DTSTAMP
                    evt_line = re.sub(r'DTSTAMP;[^:]*:', r'DTSTAMP:', evt_line)
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
                            summary_value = translate_text(summary_value)
                            evt_line = 'SUMMARY:' + summary_value
                        elif evt_line.startswith('LOCATION:'):
                            location_value = evt_line[len('LOCATION:'):]
                            location_value = translate_text(location_value)
                            evt_line = 'LOCATION:' + location_value
                        elif evt_line.startswith('DESCRIPTION:'):
                            description_value = evt_line[len('DESCRIPTION:'):]
                            description_value = translate_text(description_value)
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

    # Include the VTIMEZONE component (same as before)
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

    # Function to fold lines longer than 75 octets (same as before)
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
    output_ics_file = f'{schedule_name}.ics'
    with open(output_ics_file, 'w', encoding='utf-8') as f:
        f.write(corrected_data)

    # Save updated UID mappings to file (overwrite existing file)
    with open(uid_mappings_file, 'w', encoding='utf-8') as f:
        json.dump(uid_mappings, f, ensure_ascii=False, indent=2)

def translate_text(text):
    """
    Translate text based on the translation_map.
    """
    for pl_word, en_word in translation_map.items():
        # Use word boundaries to avoid partial replacements
        text = re.sub(r'\b' + re.escape(pl_word) + r'\b', en_word, text, flags=re.IGNORECASE)
    return text

# Main processing loop
if __name__ == '__main__':
    for schedule in SCHEDULE_LINKS:
        schedule_name = schedule.get('name')
        calendar_url = schedule.get('url')
        if schedule_name and calendar_url:
            print(f'Processing schedule: {schedule_name}')
            process_calendar(schedule_name, calendar_url)
        else:
            print('Invalid schedule configuration:', schedule)
