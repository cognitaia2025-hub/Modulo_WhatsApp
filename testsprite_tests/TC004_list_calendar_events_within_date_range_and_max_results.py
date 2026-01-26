import requests
from datetime import datetime, timedelta, timezone

BASE_URL = "http://localhost:8000"
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}

def test_list_calendar_events_within_date_range_and_max_results():
    now = datetime.now(timezone.utc)
    start_range = now + timedelta(days=1)
    end_range = now + timedelta(days=5)

    # Create events via '/invoke' endpoint using natural language commands
    for i in range(5):
        event_date = (start_range + timedelta(days=i)).strftime("%Y-%m-%d")
        user_input = f"Crear evento Test Event {i+1} el {event_date} de 09:00 a 10:00 en Location {i+1} con descripción Description for event {i+1}"
        payload_create = {"user_input": user_input}

        response = requests.post(
            f"{BASE_URL}/invoke",
            json=payload_create,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert response.status_code == 200, f"Failed to create event {i+1}"
        resp_json = response.json()
        assert resp_json.get("status") == "success", f"Create event {i+1} response status not success"
        assert "result" in resp_json, f"Create event {i+1} has no result field"

    # List events in range with max_results=3
    list_start = start_range.strftime("%Y-%m-%dT%H:%M:%S")
    list_end = (end_range + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    max_results = 3
    user_input_list = f"Listar eventos desde {list_start} hasta {list_end} máximo {max_results}"

    payload_list = {"user_input": user_input_list}

    response_list = requests.post(
        f"{BASE_URL}/invoke",
        json=payload_list,
        headers=HEADERS,
        timeout=TIMEOUT
    )
    assert response_list.status_code == 200, "List events request failed"
    resp_list_json = response_list.json()
    assert resp_list_json.get("status") == "success", "List events response status not success"
    events = resp_list_json.get("result")
    assert isinstance(events, list), "List events result is not a list"
    assert len(events) <= max_results, f"Returned more than {max_results} events"

    # Validate each event is within date range
    start_dt = datetime.strptime(list_start, "%Y-%m-%dT%H:%M:%S")
    end_dt = datetime.strptime(list_end, "%Y-%m-%dT%H:%M:%S")
    for event in events:
        event_start_str = event.get("start_datetime") or event.get("start")
        event_end_str = event.get("end_datetime") or event.get("end")
        assert event_start_str is not None, "Event missing start datetime"
        assert event_end_str is not None, "Event missing end datetime"

        event_start_dt = datetime.strptime(event_start_str, "%Y-%m-%dT%H:%M:%S")
        event_end_dt = datetime.strptime(event_end_str, "%Y-%m-%dT%H:%M:%S")

        assert start_dt <= event_start_dt <= end_dt, "Event start datetime out of range"
        assert start_dt <= event_end_dt <= end_dt, "Event end datetime out of range"

    # Cleanup: delete created events by natural language queries
    for i in range(5):
        event_date = (start_range + timedelta(days=i)).strftime("%Y-%m-%d")
        user_input_delete = f"Eliminar evento Test Event {i+1} el {event_date} a las 09:00"
        payload_delete = {"user_input": user_input_delete}
        try:
            requests.post(
                f"{BASE_URL}/invoke",
                json=payload_delete,
                headers=HEADERS,
                timeout=TIMEOUT
            )
        except Exception:
            pass

test_list_calendar_events_within_date_range_and_max_results()
