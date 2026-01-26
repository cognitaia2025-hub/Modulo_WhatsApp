import requests
import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}


def test_tc006_delete_calendar_event_using_natural_language_query():
    """
    Test the delete_event_tool function by:
    1. Creating a calendar event for deletion test.
    2. Using the /invoke endpoint with a natural language query to delete the event within a date range.
    3. Verifying the deletion confirmation message.
    4. Ensuring the event is no longer listable.
    """
    # Step 1: Create an event first to delete
    now = datetime.datetime.utcnow()
    start_datetime = (now + datetime.timedelta(minutes=5)).replace(microsecond=0).isoformat()
    end_datetime = (now + datetime.timedelta(minutes=65)).replace(microsecond=0).isoformat()
    summary = "Test Event to Delete"
    location = "Test Location"
    description = "Event created to test deletion via natural language query."

    create_event_payload = {
        "user_input": (
            f"crear evento titulado '{summary}' desde {start_datetime} "
            f"hasta {end_datetime} ubicacion {location} descripcion {description}"
        )
    }

    event_id = None
    try:
        # Create event via /invoke
        create_resp = requests.post(
            f"{BASE_URL}/invoke", json=create_event_payload, headers=HEADERS, timeout=TIMEOUT
        )
        assert create_resp.status_code == 200, f"Create event failed: {create_resp.text}"
        create_data = create_resp.json()
        assert create_data.get("status") == "success", f"Create event unsuccessful: {create_data}"

        # It's not explicitly provided how to extract event ID; Assume confirmation contains URL with ID
        result_text = create_data.get("result", "")
        # Simple heuristic to find event ID (Google Calendar event URLs have a predictable pattern)
        import re

        event_id_match = re.search(r"/events/([a-zA-Z0-9_\-]+)", str(result_text))
        if event_id_match:
            event_id = event_id_match.group(1)

        # Step 2: Delete event using natural language query within date range
        # Use a user query fully in Spanish that would match the created event
        delete_user_query = f"eliminar evento titulado '{summary}'"

        delete_payload = {
            "user_input": (
                f"eliminar evento desde {start_datetime} hasta {end_datetime} que contenga '{summary}'"
            )
        }

        delete_resp = requests.post(
            f"{BASE_URL}/invoke", json=delete_payload, headers=HEADERS, timeout=TIMEOUT
        )
        assert delete_resp.status_code == 200, f"Delete event failed: {delete_resp.text}"
        delete_data = delete_resp.json()
        assert delete_data.get("status") == "success", f"Delete event unsuccessful: {delete_data}"
        confirmation = delete_data.get("result", None)
        assert confirmation is not None, "Delete result missing"
        assert isinstance(confirmation, (str, dict)), "Unexpected delete result format"

        # Step 3: Verify the event no longer exists by listing events in the date range
        list_payload = {
            "user_input": (
                f"listar eventos desde {start_datetime} hasta {end_datetime}"
            )
        }
        list_resp = requests.post(
            f"{BASE_URL}/invoke", json=list_payload, headers=HEADERS, timeout=TIMEOUT
        )
        assert list_resp.status_code == 200, f"List events failed: {list_resp.text}"
        list_data = list_resp.json()
        assert list_data.get("status") == "success", f"List events unsuccessful: {list_data}"
        events = list_data.get("result")
        # result can be array or dict, try best effort to verify event is not present
        if isinstance(events, list):
            summaries = [e.get("summary", "") for e in events if isinstance(e, dict)]
            assert summary not in summaries, "Deleted event still appears in event list"
        elif isinstance(events, dict):
            # If result is dict with events inside some key (e.g. items)
            items = events.get("items", [])
            summaries = [e.get("summary", "") for e in items if isinstance(e, dict)]
            assert summary not in summaries, "Deleted event still appears in event list"

    finally:
        # Cleanup: Just in case delete did not remove the event, attempt deletion directly via query
        if event_id:
            # Try delete again to ensure no residue
            delete_query = (
                f"eliminar evento desde {start_datetime} hasta {end_datetime} que contenga '{summary}'"
            )
            try:
                requests.post(
                    f"{BASE_URL}/invoke",
                    json={"user_input": delete_query},
                    headers=HEADERS,
                    timeout=TIMEOUT,
                )
            except Exception:
                pass


test_tc006_delete_calendar_event_using_natural_language_query()
