from flask import Flask, render_template, request, jsonify
from urllib.parse import urlparse, parse_qs, quote, unquote
from datetime import datetime, timedelta, timezone
import requests
import icalendar
import recurring_ical_events

app = Flask(__name__)

def extract_calendar_id(link):
    parsed = urlparse(link)
    query = parse_qs(parsed.query)

    if "src" in query:
        return unquote(query["src"][0])
    if "cid" in query:
        return unquote(query["cid"][0])
    if "/calendar/ical/" in parsed.path:
        parts = parsed.path.split("/calendar/ical/")
        if len(parts) > 1:
            return unquote(parts[1].split("/")[0])
    raise ValueError("Could not find calendar ID. Use a public Google Calendar link.")

def build_ics_url(calendar_id):
    encoded_id = quote(calendar_id, safe="")
    return f"https://calendar.google.com/calendar/ical/{encoded_id}/public/basic.ics"

def fetch_calendar_events(calendar_link):
    calendar_id = extract_calendar_id(calendar_link)
    ics_url = build_ics_url(calendar_id)

    print("Calendar ID:", calendar_id)
    print("ICS URL:", ics_url)
    response = requests.get(ics_url, timeout=10)
    print("Google response status:", response.status_code)
    if response.status_code != 200:
        raise ValueError("Could not access calendar. Make sure it is public.")
    
    calendar = icalendar.Calendar.from_ical(response.content)
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=90)
    events = recurring_ical_events.of(calendar).between(now, end_date)
    result = []

    for event in events:
        title = str(event.get("summary", "No title"))
        start = event.get("dtstart").dt
        end = event.get("dtend").dt if event.get("dtend") else start
        if not isinstance(start, datetime):
            start = datetime.combine(start, datetime.min.time())
        if not isinstance(end, datetime):
            end = datetime.combine(end, datetime.min.time())
        result.append({
            "title": title,
            "start": start.strftime("%d.%m.%Y %H:%M"),
            "end": end.strftime("%d.%m.%Y %H:%M")
        })

    print("Events found:", len(result))
    return result

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/calendar", methods=["POST"])
def api_calendar():
    data = request.get_json()
    calendar_link = data.get("calendarLink")

    if not calendar_link:
        return jsonify({"error": "Calendar link is required"}), 400
    try:
        events = fetch_calendar_events(calendar_link)
        return jsonify(events)
    except Exception as i:
        print("ERROR:", str(i))
        return jsonify({"error": str(i)}), 400

if __name__ == "__main__":
    app.run(debug=True)