import requests
from datetime import datetime, timedelta
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}

def create_event(start_datetime, end_datetime, summary, location=None, description=None):
    payload = {
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "summary": summary
    }
    if location:
        payload["location"] = location
    if description:
        payload["description"] = description

    response = requests.post(f"{BASE_URL}/invoke", json={
        "user_input": f"create event {summary} from {start_datetime} to {end_datetime}" + 
                      (f" at {location}" if location else "") + 
                      (f" about {description}" if description else "")
    }, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    assert data.get("status") == "success"
    # Extract event id or link from result if available
    result = data.get("result", {})
    # Attempt to extract event ID or unique identifier from the returned result message if possible
    # For safety, just return the whole result text as identifier (postpone endpoint uses natural language)
    return result

def delete_event(start_datetime, end_datetime, user_query):
    payload = {
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "user_query": user_query
    }
    response = requests.post(f"{BASE_URL}/invoke", json={
        "user_input": f"delete event {user_query} between {start_datetime} and {end_datetime}"
    }, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    assert data.get("status") == "success"
    return data.get("result", "")

def postpone_event(start_datetime, end_datetime, user_query, new_start_datetime, new_end_datetime):
    payload = {
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "user_query": user_query,
        "new_start_datetime": new_start_datetime,
        "new_end_datetime": new_end_datetime
    }
    # According to PRD, postpone is performed by natural language query via /invoke
    # We need to craft a natural language user_input reflecting the postpone with all required dates.

    # Format a natural language query for postponing the event described in user_query within the date range to new dates:
    user_input = (
        f"postpone event {user_query} between {start_datetime} and {end_datetime} "
        f"to start at {new_start_datetime} and end at {new_end_datetime}"
    )

    response = requests.post(f"{BASE_URL}/invoke", json={
        "user_input": user_input
    }, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    assert data.get("status") == "success"
    result_message = data.get("result", "")
    assert isinstance(result_message, dict) or isinstance(result_message, str)
    return result_message

def test_postpone_calendar_event_using_natural_language_query():
    # Step 1: Create a new event to be postponed later
    now = datetime.utcnow()
    original_start = (now + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
    original_end = (now + timedelta(minutes=35)).strftime("%Y-%m-%dT%H:%M:%S")
    summary = "Test Postpone Event TC005"
    location = "Conference Room"
    description = "Initial event description for postpone test"

    # Create event using /invoke with natural language command
    create_payload = f"create event {summary} from {original_start} to {original_end} at {location} about {description}"

    create_response = requests.post(f"{BASE_URL}/invoke", json={"user_input": create_payload}, headers=HEADERS, timeout=TIMEOUT)
    try:
        create_response.raise_for_status()
        create_data = create_response.json()
        assert create_data.get("status") == "success"
        # Wait briefly to ensure event is registered before postponing
        time.sleep(1)

        # Step 2: Use postpone event tool via natural language query
        # We'll postpone the event to a new time range
        new_start = (now + timedelta(minutes=45)).strftime("%Y-%m-%dT%H:%M:%S")
        new_end = (now + timedelta(minutes=75)).strftime("%Y-%m-%dT%H:%M:%S")

        # The date range to find the event is the original start and end datetime
        postponed_message = postpone_event(
            start_datetime=original_start,
            end_datetime=original_end,
            user_query=summary,
            new_start_datetime=new_start,
            new_end_datetime=new_end
        )
        assert postponed_message is not None
        # The message should contain confirmation or clarifying text (strings)
        if isinstance(postponed_message, dict):
            # If the result is a dict with message field or similar
            confirmation_text = postponed_message.get("message") or str(postponed_message)
        else:
            confirmation_text = postponed_message
        assert isinstance(confirmation_text, str)
        assert len(confirmation_text) > 0

    finally:
        # Clean up created event by deleting it using natural language query and original timestamps
        delete_input = f"{summary}"
        try:
            delete_response = requests.post(f"{BASE_URL}/invoke", json={
                "user_input": f"delete event {delete_input} between {original_start} and {(now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')}"
            }, headers=HEADERS, timeout=TIMEOUT)
            delete_response.raise_for_status()
            delete_data = delete_response.json()
            assert delete_data.get("status") == "success"
        except Exception:
            pass

test_postpone_calendar_event_using_natural_language_query()