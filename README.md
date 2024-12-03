# UEK Calendar

This repository fetches and processes the UEK schedule to make it compatible with Apple Calendar.

## How to Use

1. **Fork this repository**.

2. **Update the calendar URL**:

   - Edit `config.py` and replace the `CALENDAR_URL` with your own calendar link.

3. **Enable GitHub Actions**:

   - Go to the **Actions** tab in your forked repository.
   - Enable workflows by clicking **"I understand my workflows, go ahead and enable them"**.

4. **Set Up GitHub Pages**:

   - Go to **Settings** > **Pages**.
   - Under **Source**, select `main` branch and root (`/`).
   - Click **Save**.

5. **Access Your Calendar**:

   - Your corrected calendar will be available at:
     ```
     https://yourusername.github.io/uek-calendar/corrected_calendar.ics
     ```

6. **Subscribe in Apple Calendar**:

   - Use the URL above to subscribe to your calendar in Apple Calendar.

## Customization

- **Update Frequency**:

  - By default, the calendar updates twice a day.
  - To change this, edit the cron schedule in `.github/workflows/update_calendar.yml`.

- **Event Filtering**:

  - The script excludes placeholder events.
  - Modify `update_calendar.py` if you need to adjust which events are filtered.

## Dependencies

- The script uses Python 3 and the `requests` library.
- Dependencies are handled automatically by GitHub Actions.

## License

This project is licensed under the MIT License.
